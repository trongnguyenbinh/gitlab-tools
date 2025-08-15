#!/usr/bin/env python3
"""
Unit tests for GitLab Cloner.

This module contains comprehensive tests for the GitLab cloner functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from pathlib import Path
import os

from gitlab_cloner import GitLabCloner
from config import Config


class TestGitLabCloner(unittest.TestCase):
    """Test cases for GitLabCloner class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.gitlab_url = "https://gitlab.example.com"
        self.access_token = "test-token"
        self.destination_path = self.temp_dir
        
        # Mock GitLab connection
        with patch('gitlab_cloner.gitlab.Gitlab'):
            self.cloner = GitLabCloner(
                self.gitlab_url,
                self.access_token,
                self.destination_path
            )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test GitLabCloner initialization."""
        self.assertEqual(self.cloner.gitlab_url, self.gitlab_url)
        self.assertEqual(self.cloner.access_token, self.access_token)
        self.assertEqual(self.cloner.destination_path, Path(self.destination_path))
        self.assertIsNotNone(self.cloner.logger)
        self.assertIsNotNone(self.cloner.stats)
    
    @patch('gitlab_cloner.gitlab.Gitlab')
    def test_authenticate_success(self, mock_gitlab):
        """Test successful authentication."""
        # Setup mock
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_gitlab_instance = Mock()
        mock_gitlab_instance.user = mock_user
        mock_gitlab.return_value = mock_gitlab_instance
        
        cloner = GitLabCloner(self.gitlab_url, self.access_token, self.destination_path)
        result = cloner.authenticate()
        
        self.assertTrue(result)
        mock_gitlab_instance.auth.assert_called_once()
    
    @patch('gitlab_cloner.gitlab.Gitlab')
    def test_authenticate_failure(self, mock_gitlab):
        """Test authentication failure."""
        # Setup mock to raise exception
        mock_gitlab_instance = Mock()
        mock_gitlab_instance.auth.side_effect = Exception("Auth failed")
        mock_gitlab.return_value = mock_gitlab_instance
        
        cloner = GitLabCloner(self.gitlab_url, self.access_token, self.destination_path)
        result = cloner.authenticate()
        
        self.assertFalse(result)
    
    def test_get_group_by_id(self):
        """Test getting group by numeric ID."""
        # Setup mock
        mock_group = Mock()
        mock_group.name = "Test Group"
        mock_group.id = 123
        self.cloner.gl.groups.get.return_value = mock_group
        
        result = self.cloner.get_group("123")
        
        self.assertEqual(result, mock_group)
        self.cloner.gl.groups.get.assert_called_once_with(123)
    
    def test_get_group_by_path(self):
        """Test getting group by path."""
        # Setup mock
        mock_group = Mock()
        mock_group.name = "Test Group"
        mock_group.id = 123
        self.cloner.gl.groups.get.return_value = mock_group
        
        result = self.cloner.get_group("test/group")
        
        self.assertEqual(result, mock_group)
        self.cloner.gl.groups.get.assert_called_once_with("test/group")
    
    def test_get_group_not_found(self):
        """Test getting non-existent group."""
        # Setup mock to raise exception
        self.cloner.gl.groups.get.side_effect = Exception("Group not found")
        
        result = self.cloner.get_group("nonexistent")
        
        self.assertIsNone(result)
    
    @patch('gitlab_cloner.Repo')
    def test_clone_repository_success(self, mock_repo):
        """Test successful repository cloning."""
        # Setup mock project
        mock_project = Mock()
        mock_project.name = "test-repo"
        mock_project.http_url_to_repo = "https://gitlab.example.com/test/repo.git"
        
        # Setup mock repo
        mock_repo.clone_from.return_value = Mock()
        
        local_path = Path(self.temp_dir)
        result = self.cloner.clone_repository(mock_project, local_path)
        
        self.assertTrue(result)
        self.assertEqual(self.cloner.stats['repositories_cloned'], 1)
        mock_repo.clone_from.assert_called_once()
    
    @patch('gitlab_cloner.Repo')
    def test_clone_repository_already_exists(self, mock_repo):
        """Test cloning when repository already exists."""
        # Create existing directory
        mock_project = Mock()
        mock_project.name = "test-repo"
        existing_repo_path = Path(self.temp_dir) / "test-repo"
        existing_repo_path.mkdir()
        
        local_path = Path(self.temp_dir)
        result = self.cloner.clone_repository(mock_project, local_path)
        
        self.assertTrue(result)
        self.assertEqual(self.cloner.stats['repositories_skipped'], 1)
        mock_repo.clone_from.assert_not_called()
    
    def test_process_group_items(self):
        """Test processing group items (projects and subgroups)."""
        # Setup mock group
        mock_group = Mock()
        mock_group.name = "Test Group"
        
        # Setup mock projects
        mock_project1 = Mock()
        mock_project1.name = "project1"
        mock_project1.http_url_to_repo = "https://gitlab.example.com/test/project1.git"
        
        mock_project2 = Mock()
        mock_project2.name = "project2"
        mock_project2.http_url_to_repo = "https://gitlab.example.com/test/project2.git"
        
        mock_group.projects.list.return_value = [mock_project1, mock_project2]
        
        # Setup mock subgroups
        mock_subgroup = Mock()
        mock_subgroup.name = "subgroup1"
        mock_subgroup.id = 456
        
        mock_group.subgroups.list.return_value = [mock_subgroup]
        
        # Setup mock for getting full subgroup
        mock_full_subgroup = Mock()
        self.cloner.gl.groups.get.return_value = mock_full_subgroup
        
        # Mock clone_repository method
        with patch.object(self.cloner, 'clone_repository', return_value=True):
            local_path = Path(self.temp_dir)
            subgroups = self.cloner.process_group_items(mock_group, local_path)
        
        # Verify results
        self.assertEqual(len(subgroups), 1)
        self.assertEqual(subgroups[0][0], mock_full_subgroup)
        self.assertTrue((local_path / "subgroup1").exists())


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.config = Config(self.config_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_empty_config(self):
        """Test initialization with empty config."""
        self.assertEqual(self.config.config, {})
    
    def test_get_set_config_values(self):
        """Test getting and setting configuration values."""
        self.config.set("test_key", "test_value")
        self.assertEqual(self.config.get("test_key"), "test_value")
        self.assertEqual(self.config.get("nonexistent", "default"), "default")
    
    def test_save_load_config(self):
        """Test saving and loading configuration."""
        self.config.set("gitlab_url", "https://gitlab.example.com")
        self.config.set("timeout", 30)
        
        # Save config
        result = self.config.save_config()
        self.assertTrue(result)
        
        # Load config in new instance
        new_config = Config(self.config_file)
        self.assertEqual(new_config.get("gitlab_url"), "https://gitlab.example.com")
        self.assertEqual(new_config.get("timeout"), 30)
    
    def test_validate_gitlab_url(self):
        """Test GitLab URL validation."""
        self.assertTrue(self.config.validate_gitlab_url("https://gitlab.com"))
        self.assertTrue(self.config.validate_gitlab_url("http://gitlab.example.com"))
        self.assertFalse(self.config.validate_gitlab_url(""))
        self.assertFalse(self.config.validate_gitlab_url("invalid-url"))
        self.assertFalse(self.config.validate_gitlab_url("ftp://gitlab.com"))
    
    def test_validate_access_token(self):
        """Test access token validation."""
        self.assertTrue(self.config.validate_access_token("glpat-xxxxxxxxxxxxxxxxxxxx"))
        self.assertTrue(self.config.validate_access_token("valid-token"))
        self.assertFalse(self.config.validate_access_token(""))
        self.assertFalse(self.config.validate_access_token("   "))
    
    def test_validate_destination_path(self):
        """Test destination path validation."""
        self.assertTrue(self.config.validate_destination_path(self.temp_dir))
        self.assertTrue(self.config.validate_destination_path("/tmp"))
        self.assertFalse(self.config.validate_destination_path(""))


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
