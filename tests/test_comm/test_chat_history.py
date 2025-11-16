"""Tests for ChatHistoryManager."""

import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

from stock_tracker.comm.chat_history import ChatHistoryManager


class TestChatHistoryManager:
    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Setup test database for each test."""
        import time
        import uuid

        # Create unique temporary database file with timestamp and uuid
        temp_path = (
            f"/tmp/test_chat_history_{int(time.time())}_{uuid.uuid4().hex[:8]}.db"
        )

        # Initialize ChatHistoryManager with temporary database
        self.chat_manager = ChatHistoryManager(db_path=temp_path)
        self.temp_db_path = temp_path
        yield

        # Close any connections and clean up
        try:
            if hasattr(self.chat_manager, "_get_connection"):
                conn = self.chat_manager._get_connection()
                conn.close()
        except:
            pass

        # Clean up the temp file
        try:
            os.unlink(self.temp_db_path)
        except:
            pass

    def test_database_initialization(self):
        """Test that database is properly initialized."""
        # Test by trying to store and retrieve a message
        test_chat = "init_test_chat"
        test_message = "init_test_message"

        # This should work if database is properly initialized
        self.chat_manager.store_user_message(test_chat, test_message)
        history = self.chat_manager.get_chat_history(test_chat)

        assert len(history) == 1
        assert history[0]["text"] == test_message

    def test_store_user_message(self):
        """Test storing user messages."""
        chat_id = "test_chat_123"
        message = "Hello, how are you?"

        self.chat_manager.store_user_message(chat_id, message)

        # Verify message was stored using the chat manager's connection
        history = self.chat_manager.get_chat_history(chat_id)

        assert len(history) == 1
        assert history[0]["chat_id"] == chat_id
        assert history[0]["text"] == message
        assert history[0]["message_type"] == "user"

    def test_store_bot_response(self):
        """Test storing bot responses."""
        chat_id = "test_chat_123"
        response = "I'm doing well, thanks!"

        self.chat_manager.store_bot_response(chat_id, response)

        # Verify response was stored using the chat manager's connection
        history = self.chat_manager.get_chat_history(chat_id)

        assert len(history) == 1
        assert history[0]["chat_id"] == chat_id
        assert history[0]["text"] == response
        assert history[0]["message_type"] == "bot"

    def test_get_chat_history(self):
        """Test retrieving chat history."""
        chat_id = "test_chat_456"

        # Store some messages
        self.chat_manager.store_user_message(chat_id, "First message")
        self.chat_manager.store_bot_response(chat_id, "First response")
        self.chat_manager.store_user_message(chat_id, "Second message")

        # Get history
        history = self.chat_manager.get_chat_history(chat_id, limit=5)

        assert len(history) == 3

        # Check order (should be chronological)
        assert history[0]["text"] == "First message"
        assert history[0]["message_type"] == "user"
        assert history[1]["text"] == "First response"
        assert history[1]["message_type"] == "bot"
        assert history[2]["text"] == "Second message"
        assert history[2]["message_type"] == "user"

    def test_get_chat_history_with_limit(self):
        """Test retrieving chat history with limit."""
        chat_id = "test_chat_789"

        # Store more messages than limit
        for i in range(5):
            self.chat_manager.store_user_message(chat_id, f"Message {i}")

        # Get limited history
        history = self.chat_manager.get_chat_history(chat_id, limit=3)

        assert len(history) == 3
        # Should get the most recent 3 messages
        assert history[0]["text"] == "Message 2"
        assert history[1]["text"] == "Message 3"
        assert history[2]["text"] == "Message 4"

    def test_get_chat_history_empty(self):
        """Test retrieving history for non-existent chat."""
        history = self.chat_manager.get_chat_history("non_existent_chat")
        assert history == []

    def test_get_conversation_summary_with_history(self):
        """Test conversation summarization with existing history."""
        chat_id = "test_chat_summary"

        # Store conversation
        self.chat_manager.store_user_message(chat_id, "What's Apple's stock price?")
        self.chat_manager.store_bot_response(
            chat_id, "Apple (AAPL) is currently trading at $180.25"
        )
        self.chat_manager.store_user_message(chat_id, "What about Tesla?")

        summary = self.chat_manager.get_conversation_summary(chat_id, limit=5)

        # Should include conversation context
        assert "User: What's Apple's stock price?" in summary
        assert "Bot: Apple (AAPL) is currently trading at $180.25" in summary
        assert "User: What about Tesla?" in summary

    def test_get_conversation_summary_empty_history(self):
        """Test conversation summarization with no history."""
        summary = self.chat_manager.get_conversation_summary("empty_chat", limit=5)
        assert summary == "No previous conversation history."

    def test_store_with_metadata(self):
        """Test storing messages with metadata."""
        chat_id = "test_chat_meta"
        message = "Test with metadata"
        metadata = {"user_id": 12345, "username": "testuser"}

        self.chat_manager.store_user_message(
            chat_id, message, user_id="12345", username="testuser", metadata=metadata
        )

        # Verify metadata was stored by getting the message
        history = self.chat_manager.get_chat_history(chat_id)

        assert len(history) == 1
        assert history[0]["text"] == message
        assert history[0]["metadata"] == metadata
        assert history[0]["user_id"] == "12345"
        assert history[0]["username"] == "testuser"

    def test_multiple_chats_isolation(self):
        """Test that different chats are properly isolated."""
        chat1 = "chat_1"
        chat2 = "chat_2"

        # Store messages in different chats
        self.chat_manager.store_user_message(chat1, "Message in chat 1")
        self.chat_manager.store_user_message(chat2, "Message in chat 2")

        # Get history for each chat
        history1 = self.chat_manager.get_chat_history(chat1)
        history2 = self.chat_manager.get_chat_history(chat2)

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["text"] == "Message in chat 1"
        assert history2[0]["text"] == "Message in chat 2"

    def test_thread_safety(self):
        """Test basic thread safety (connection per thread)."""
        import threading

        chat_id = "thread_test_chat"
        results = []

        def store_message(thread_id):
            try:
                self.chat_manager.store_user_message(
                    chat_id, f"Message from thread {thread_id}"
                )
                results.append(True)
            except Exception as e:
                results.append(False)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=store_message, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert all(results), "All thread operations should succeed"

        # Verify all messages were stored
        history = self.chat_manager.get_chat_history(chat_id)
        assert len(history) == 5
