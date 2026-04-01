"""Tests for TopicClusterManager."""

import time
from agent.core.topic_clustering import TopicCluster, TopicClusterManager


def test_topic_cluster_creation():
    """Test creating a topic cluster."""
    cluster = TopicCluster(
        topic_name="feelings",
        frequency=5,
        mood_associations={"INTERESTED": 0.8, "ANALYTICAL": 0.5},
    )
    
    assert cluster.topic_name == "feelings"
    assert cluster.frequency == 5
    assert cluster.mood_associations["INTERESTED"] == 0.8
    assert cluster.calculate_importance() > 0


def test_topic_cluster_manager_add_topics():
    """Test adding and retrieving topics."""
    manager = TopicClusterManager()
    manager.add_topics(["feelings", "work"], current_mood="INTERESTED")
    
    clusters = manager.get_all()
    assert len(clusters) >= 2
    
    feelings = manager.get_cluster("feelings")
    assert feelings is not None
    assert feelings.frequency == 2  # Default 1 + 1 from add_topics


def test_topic_cluster_co_occurrence():
    """Test co-occurrence tracking."""
    manager = TopicClusterManager()
    
    manager.add_topics(["feelings", "work"], current_mood="INTERESTED")
    manager.add_topics(["feelings", "day"], current_mood="INTERESTED")
    
    feelings = manager.get_cluster("feelings")
    assert feelings.co_occurrences.get("work", 0) > 0
    assert feelings.co_occurrences.get("day", 0) > 0


def test_topic_cluster_importance_decay():
    """Test exponential decay of importance."""
    cluster = TopicCluster(topic_name="old_topic", frequency=10)
    old_importance = cluster.calculate_importance()
    
    cluster.last_seen = time.time() - (24 * 3600)
    decayed_importance = cluster.calculate_importance()
    
    assert decayed_importance < old_importance


def test_topic_manager_get_summary():
    """Test topic summary generation."""
    manager = TopicClusterManager()
    manager.add_topics(["python", "coding"], current_mood="INTERESTED")
    
    summary = manager.get_summary(n=5)
    assert "Key topics" in summary
    assert "python" in summary or "coding" in summary
