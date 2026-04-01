#!/usr/bin/env python3
"""Standalone CLI for pose extraction (headless, no server needed).

Usage:
  python extract.py --video /path/to/video.mp4 --name walk --skip 2
  python extract.py --video /path/to/video.mp4 --name idle --output ./my_poses/
"""

import argparse
import logging
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from agent.ml.pose_extractor import PoseExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("extract")


def main():
    parser = argparse.ArgumentParser(description="Extract poses from video")
    parser.add_argument("--video", required=True, help="Path to input video file")
    parser.add_argument("--name", required=True, help="Name for the pose sequence")
    parser.add_argument("--output", default=None, help="Output directory (default: tmp/<name>)")
    parser.add_argument("--skip", type=int, default=1, help="Process every Nth frame (default: 1 = all)")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        logger.error(f"Video not found: {video_path}")
        sys.exit(1)

    output_dir = args.output or str(Path(__file__).resolve().parent / "tmp" / args.name)

    logger.info(f"Extracting poses from: {video_path}")
    logger.info(f"Pose name: {args.name}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Skip frames: {args.skip}")

    extractor = PoseExtractor()
    result = extractor.analyze_video(
        video_path=str(video_path),
        output_dir=output_dir,
        pose_name=args.name,
        skip_frames=args.skip,
    )

    if result["success"]:
        logger.info("=" * 60)
        logger.info("EXTRACTION COMPLETE")
        logger.info(f"  Total frames:    {result['total_frames']}")
        logger.info(f"  Detected frames: {result['detected_frames']}")
        logger.info(f"  Keyframes stored: {result['keyframes_stored']}")
        logger.info(f"  Detection rate:  {result['detection_rate']:.1%}")
        logger.info(f"  Storage:         {result['storage_path']}")
        logger.info("=" * 60)
    else:
        logger.error(f"Extraction failed: {result.get('error', 'unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
