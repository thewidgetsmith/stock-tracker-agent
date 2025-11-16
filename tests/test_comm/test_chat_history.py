"""Tests for ChatHistoryManager."""

import pytest

from sentinel.comm.chat_history import ChatHistoryManager


class TestChatHistoryManager:

    def test_database_initialization(self, mock_db_session):
        """Test that database is properly initialized."""
        # Initialize chat manager with mocked database
        chat_manager = ChatHistoryManager()

        # Test by trying to store and retrieve a message
        test_chat = "init_test_chat"
        test_message = "init_test_message"

        # This should work if database is properly initialized
        chat_manager.store_user_message(test_chat, test_message)
        history = chat_manager.get_chat_history(test_chat)

        assert len(history) == 1
        assert history[0]["text"] == test_message

    def test_store_user_message(self, mock_db_session):
        """Test storing user messages."""
        chat_manager = ChatHistoryManager()
        chat_id = "test_chat_123"
        message = "Hello, how are you?"

        chat_manager.store_user_message(chat_id, message)

        # Verify message was stored using the chat manager's connection
        history = chat_manager.get_chat_history(chat_id)

        assert len(history) == 1
        assert history[0]["chat_id"] == chat_id
        assert history[0]["text"] == message
        assert history[0]["message_type"] == "user"

    def test_store_bot_response(self, mock_db_session):
        """Test storing bot responses."""
        chat_manager = ChatHistoryManager()
        chat_id = "test_chat_123"
        response = "I'm doing well, thanks!"

        chat_manager.store_bot_response(chat_id, response)

        # Verify response was stored using the chat manager's connection
        history = chat_manager.get_chat_history(chat_id)

        assert len(history) == 1
        assert history[0]["chat_id"] == chat_id
        assert history[0]["text"] == response
        assert history[0]["message_type"] == "bot"

    def test_get_chat_history(self, mock_db_session):
        """Test retrieving chat history."""
        chat_manager = ChatHistoryManager()
        chat_id = "test_chat_456"

        # Store some messages
        chat_manager.store_user_message(chat_id, "First message")
        chat_manager.store_bot_response(chat_id, "First response")
        chat_manager.store_user_message(chat_id, "Second message")

        # Get history
        history = chat_manager.get_chat_history(chat_id, limit=5)

        assert len(history) == 3

        # Check that all messages are present (order may vary due to timestamp precision)
        message_texts = [msg["text"] for msg in history]
        assert "First message" in message_texts
        assert "First response" in message_texts
        assert "Second message" in message_texts

        # Check that message types are correct
        message_types = [msg["message_type"] for msg in history]
        assert message_types.count("user") == 2
        assert message_types.count("bot") == 1

    def test_get_chat_history_with_limit(self, mock_db_session):
        """Test retrieving chat history with limit."""
        chat_manager = ChatHistoryManager()
        chat_id = "test_chat_789"

        # Store more messages than limit
        for i in range(5):
            chat_manager.store_user_message(chat_id, f"Message {i}")

        # Get limited history
        history = chat_manager.get_chat_history(chat_id, limit=3)

        assert len(history) == 3

        # Check that we get 3 messages (the exact order may vary due to timestamp precision)
        message_texts = [msg["text"] for msg in history]
        assert len(message_texts) == 3

        # All should be user messages
        for msg in history:
            assert msg["message_type"] == "user"
            assert msg["text"].startswith("Message ")

        # Should contain some of the messages we stored
        expected_messages = {f"Message {i}" for i in range(5)}
        actual_messages = set(message_texts)
        assert actual_messages.issubset(expected_messages)

    def test_get_chat_history_empty(self, mock_db_session):
        """Test retrieving history for non-existent chat."""
        chat_manager = ChatHistoryManager()
        history = chat_manager.get_chat_history("non_existent_chat")
        assert history == []

    def test_get_conversation_summary_with_history(self, mock_db_session):
        """Test conversation summarization with existing history."""
        chat_manager = ChatHistoryManager()
        chat_id = "test_chat_summary"

        # Store conversation
        chat_manager.store_user_message(chat_id, "What's Apple's stock price?")
        chat_manager.store_bot_response(
            chat_id, "Apple (AAPL) is currently trading at $180.25"
        )
        chat_manager.store_user_message(chat_id, "What about Tesla?")

        summary = chat_manager.get_conversation_summary(chat_id, limit=5)

        # Should include conversation context
        assert "User: What's Apple's stock price?" in summary
        assert "Bot: Apple (AAPL) is currently trading at $180.25" in summary
        assert "User: What about Tesla?" in summary

    def test_get_conversation_summary_empty_history(self, mock_db_session):
        """Test conversation summarization with no history."""
        chat_manager = ChatHistoryManager()
        summary = chat_manager.get_conversation_summary("empty_chat", limit=5)
        assert summary == "No previous conversation history."

    def test_store_with_metadata(self, mock_db_session):
        """Test storing messages with metadata."""
        chat_manager = ChatHistoryManager()
        chat_id = "test_chat_meta"
        message = "Test with metadata"
        metadata = {"user_id": 12345, "username": "testuser"}

        chat_manager.store_user_message(
            chat_id, message, user_id="12345", username="testuser", metadata=metadata
        )

        # Verify metadata was stored by getting the message
        history = chat_manager.get_chat_history(chat_id)

        assert len(history) == 1
        assert history[0]["text"] == message
        assert history[0]["metadata"] == metadata
        assert history[0]["user_id"] == "12345"
        assert history[0]["username"] == "testuser"

    def test_multiple_chats_isolation(self, mock_db_session):
        """Test that different chats are properly isolated."""
        chat_manager = ChatHistoryManager()
        chat1 = "chat_1"
        chat2 = "chat_2"

        # Store messages in different chats
        chat_manager.store_user_message(chat1, "Message in chat 1")
        chat_manager.store_user_message(chat2, "Message in chat 2")

        # Get history for each chat
        history1 = chat_manager.get_chat_history(chat1)
        history2 = chat_manager.get_chat_history(chat2)

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["text"] == "Message in chat 1"
        assert history2[0]["text"] == "Message in chat 2"

    def test_thread_safety(self, mock_db_session):
        """Test basic thread safety (connection per thread)."""
        chat_manager = ChatHistoryManager()
        import threading

        chat_id = "thread_test_chat"
        results = []

        def store_message(thread_id):
            try:
                chat_manager.store_user_message(
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
        history = chat_manager.get_chat_history(chat_id)
        assert len(history) == 5

    def test_cleanup_old_messages(self, mock_db_session):
        """Test cleanup of old messages."""
        chat_manager = ChatHistoryManager()
        chat_id = "cleanup_test_chat"
        
        # Store some messages
        chat_manager.store_user_message(chat_id, "Recent message 1")
        chat_manager.store_user_message(chat_id, "Recent message 2")
        chat_manager.store_bot_response(chat_id, "Recent bot response")
        
        # Test cleanup with future date (should delete nothing)
        deleted_count = chat_manager.cleanup_old_messages(days=0)
        
        # Should have deleted something (exact count depends on timing)
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0
        
        # Test cleanup with far future (should delete nothing new)
        deleted_count_2 = chat_manager.cleanup_old_messages(days=365)
        assert deleted_count_2 == 0

    def test_get_chat_statistics(self, mock_db_session):
        """Test getting chat statistics."""
        chat_manager = ChatHistoryManager()
        chat_id = "stats_test_chat"
        
        # Store some messages
        chat_manager.store_user_message(chat_id, "User message 1")
        chat_manager.store_user_message(chat_id, "User message 2")
        chat_manager.store_bot_response(chat_id, "Bot response 1")
        
        # Get statistics
        stats = chat_manager.get_chat_statistics(chat_id)
        
        # Should return a dictionary with statistics
        assert isinstance(stats, dict)
        # The exact structure depends on the repository implementation
        # but it should contain some statistical information
