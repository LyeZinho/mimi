"""Unit tests for PoseDetector MediaPipe integration."""

import numpy as np
import pytest

from agent.ml import PoseDetector


class TestPoseDetectorInit:
    """Tests for PoseDetector initialization."""

    def test_detector_init_with_defaults(self):
        """Test that PoseDetector instantiates with default parameters."""
        detector = PoseDetector()
        assert detector is not None
        assert hasattr(detector, 'process_frame')
        assert callable(detector.process_frame)

    def test_detector_init_with_static_image_mode_true(self):
        """Test that PoseDetector instantiates with static_image_mode=True."""
        detector = PoseDetector(static_image_mode=True)
        assert detector is not None
        assert hasattr(detector, 'process_frame')

    def test_detector_init_with_static_image_mode_false(self):
        """Test that PoseDetector instantiates with static_image_mode=False."""
        detector = PoseDetector(static_image_mode=False)
        assert detector is not None
        assert hasattr(detector, 'process_frame')


class TestProcessFrame:
    """Tests for process_frame method."""

    @pytest.fixture
    def detector(self):
        """Provide PoseDetector instance."""
        return PoseDetector(static_image_mode=True)

    @pytest.fixture
    def dummy_frame(self):
        """Provide a dummy BGR frame (H x W x 3)."""
        # Create a dummy 480x640 BGR frame (typical resolution)
        return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

    def test_process_frame_returns_dict(self, detector, dummy_frame):
        """Test that process_frame returns a dictionary."""
        result = detector.process_frame(dummy_frame)
        assert isinstance(result, dict)

    def test_process_frame_has_required_keys(self, detector, dummy_frame):
        """Test that process_frame result contains required keys."""
        result = detector.process_frame(dummy_frame)
        required_keys = [
            'body_landmarks',
            'hand_landmarks_left',
            'hand_landmarks_right',
            'face_landmarks',
            'success',
            'frame_id'
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_process_frame_success_is_bool(self, detector, dummy_frame):
        """Test that process_frame 'success' field is boolean."""
        result = detector.process_frame(dummy_frame)
        assert isinstance(result['success'], bool)

    def test_process_frame_frame_id_is_int(self, detector, dummy_frame):
        """Test that process_frame 'frame_id' field is integer."""
        result = detector.process_frame(dummy_frame)
        assert isinstance(result['frame_id'], int)

    def test_process_frame_body_landmarks_is_dict_or_none(self, detector, dummy_frame):
        """Test that body_landmarks is dict or None."""
        result = detector.process_frame(dummy_frame)
        assert result['body_landmarks'] is None or isinstance(result['body_landmarks'], dict)

    def test_process_frame_hand_landmarks_left_is_dict_or_none(self, detector, dummy_frame):
        """Test that hand_landmarks_left is dict or None."""
        result = detector.process_frame(dummy_frame)
        assert result['hand_landmarks_left'] is None or isinstance(result['hand_landmarks_left'], dict)

    def test_process_frame_hand_landmarks_right_is_dict_or_none(self, detector, dummy_frame):
        """Test that hand_landmarks_right is dict or None."""
        result = detector.process_frame(dummy_frame)
        assert result['hand_landmarks_right'] is None or isinstance(result['hand_landmarks_right'], dict)

    def test_process_frame_face_landmarks_is_dict_or_none(self, detector, dummy_frame):
        """Test that face_landmarks is dict or None."""
        result = detector.process_frame(dummy_frame)
        assert result['face_landmarks'] is None or isinstance(result['face_landmarks'], dict)

    def test_process_frame_increments_frame_id(self, detector, dummy_frame):
        """Test that process_frame increments frame_id on successive calls."""
        result1 = detector.process_frame(dummy_frame)
        result2 = detector.process_frame(dummy_frame)
        assert result2['frame_id'] > result1['frame_id']


class TestNormalizeLandmarks:
    """Tests for normalize_landmarks method."""

    @pytest.fixture
    def detector(self):
        """Provide PoseDetector instance."""
        return PoseDetector(static_image_mode=True)

    @pytest.fixture
    def sample_landmarks(self):
        """Provide sample landmarks dict."""
        return {
            'landmarks': [
                {'x': 100, 'y': 150, 'z': 10},
                {'x': 200, 'y': 300, 'z': 20},
                {'x': 400, 'y': 450, 'z': 30},
            ]
        }

    def test_normalize_landmarks_returns_dict(self, detector, sample_landmarks):
        """Test that normalize_landmarks returns a dictionary."""
        result = detector.normalize_landmarks(sample_landmarks)
        assert isinstance(result, dict)

    def test_normalize_landmarks_has_landmarks_key(self, detector, sample_landmarks):
        """Test that normalized result has 'landmarks' key."""
        result = detector.normalize_landmarks(sample_landmarks)
        assert 'landmarks' in result

    def test_normalize_landmarks_values_in_range(self, detector, sample_landmarks):
        """Test that normalized values are in [0, 1] range."""
        result = detector.normalize_landmarks(sample_landmarks)
        for landmark in result['landmarks']:
            if isinstance(landmark, dict):
                for coord in ['x', 'y', 'z']:
                    if coord in landmark:
                        value = landmark[coord]
                        assert 0.0 <= value <= 1.0, f"{coord} value {value} out of range"

    def test_normalize_landmarks_preserves_structure(self, detector, sample_landmarks):
        """Test that normalization preserves landmarks structure."""
        result = detector.normalize_landmarks(sample_landmarks)
        assert len(result['landmarks']) == len(sample_landmarks['landmarks'])

    def test_normalize_landmarks_empty_dict(self, detector):
        """Test that normalize_landmarks handles empty dict."""
        result = detector.normalize_landmarks({})
        assert isinstance(result, dict)

    def test_normalize_landmarks_none_input(self, detector):
        """Test that normalize_landmarks handles None input gracefully."""
        result = detector.normalize_landmarks(None)
        # Should return a valid dict or None
        assert result is None or isinstance(result, dict)


class TestClose:
    """Tests for close method."""

    def test_close_method_exists(self):
        """Test that PoseDetector has close method."""
        detector = PoseDetector()
        assert hasattr(detector, 'close')
        assert callable(detector.close)

    def test_close_can_be_called(self):
        """Test that close method can be called without error."""
        detector = PoseDetector()
        detector.close()  # Should not raise


class TestPoseDetectorIntegration:
    """Integration tests for PoseDetector."""

    def test_full_workflow_init_process_close(self):
        """Test full workflow: init -> process_frame -> close."""
        detector = PoseDetector(static_image_mode=True)
        
        # Create a dummy frame
        dummy_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        
        # Process frame
        result = detector.process_frame(dummy_frame)
        assert isinstance(result, dict)
        assert result['success'] in [True, False]
        
        # Close detector
        detector.close()
