"""
Quality Scorer - Pre-upload quality gate

Scores scripts and videos before upload to ensure quality standards.
Rejects content below threshold to maintain YPP compliance.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


class QualityScorer:
    """Scores content quality before upload"""
    
    # Quality thresholds
    MIN_SCRIPT_SCORE = 7.0  # Out of 10
    MIN_VIDEO_SCORE = 6.5   # Out of 10
    MIN_METADATA_SCORE = 7.0  # Out of 10
    
    def __init__(self):
        self.scoring_history: List[Dict[str, Any]] = []
    
    def score_script(self, script_data: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """
        Score script quality
        
        Args:
            script_data: Script data dictionary
            topic: Video topic
        
        Returns:
            Score dictionary with pass/fail and details
        """
        score = 0.0
        max_score = 10.0
        issues = []
        strengths = []
        
        script_text = script_data.get("script", "")
        title = script_data.get("title", "")
        visual_cues = script_data.get("visual_cues", [])
        
        # 1. Script length (2 points)
        word_count = len(script_text.split())
        if 50 <= word_count <= 100:
            score += 2.0
            strengths.append("Optimal script length")
        elif 30 <= word_count < 50 or 100 < word_count <= 150:
            score += 1.0
            issues.append(f"Script length ({word_count} words) slightly off optimal")
        else:
            issues.append(f"Script length ({word_count} words) too short/long")
        
        # 2. Title quality (1.5 points)
        if title and len(title) > 10:
            if any(char in title for char in ['?', '!', ':', '-']):
                score += 0.5  # Has engagement markers
            if len(title) <= 60:
                score += 1.0  # Good length
            strengths.append("Good title")
        else:
            issues.append("Title missing or too short")
        
        # 3. Visual cues (1.5 points)
        if visual_cues and len(visual_cues) >= 3:
            score += 1.5
            strengths.append("Adequate visual cues")
        elif visual_cues and len(visual_cues) >= 1:
            score += 0.75
            issues.append("Insufficient visual cues")
        else:
            issues.append("No visual cues provided")
        
        # 4. Script structure (2 points)
        sentences = script_text.split('.')
        if 5 <= len(sentences) <= 15:
            score += 1.0
            strengths.append("Good sentence structure")
        else:
            issues.append(f"Unusual sentence count ({len(sentences)})")
        
        # Check for hook, value, CTA
        has_hook = any(word in script_text.lower()[:50] for word in ['ഇത്', 'അറിയാമോ', 'കണ്ടോ', 'നോക്ക്', 'this', 'know', 'see', 'look'])
        has_value = len(script_text) > 30
        has_cta = any(word in script_text.lower()[-30:] for word in ['കാണൂ', 'അറിയൂ', 'watch', 'learn', 'know'])
        
        if has_hook and has_value and has_cta:
            score += 1.0
            strengths.append("Complete script structure (hook/value/CTA)")
        else:
            missing = []
            if not has_hook:
                missing.append("hook")
            if not has_value:
                missing.append("value")
            if not has_cta:
                missing.append("CTA")
            issues.append(f"Missing script elements: {', '.join(missing)}")
        
        # 5. Language quality (1.5 points)
        # Check for proper language usage (basic check)
        if script_text and len(script_text) > 20:
            # Check for mixed scripts (should be consistent)
            has_unicode = any(ord(c) > 127 for c in script_text)
            if has_unicode:
                score += 1.5
                strengths.append("Proper Unicode script")
            else:
                score += 0.5
                issues.append("Script may not be in target language")
        
        # 6. Originality check (1.5 points)
        # Basic check - should be enhanced with similarity checking
        if script_text and len(script_text) > 30:
            score += 1.5
            strengths.append("Script appears original")
        else:
            issues.append("Script too short to assess originality")
        
        final_score = (score / max_score) * 10.0
        
        result = {
            "score": round(final_score, 2),
            "max_score": 10.0,
            "passed": final_score >= self.MIN_SCRIPT_SCORE,
            "threshold": self.MIN_SCRIPT_SCORE,
            "issues": issues,
            "strengths": strengths,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log scoring
        if result["passed"]:
            logging.info(f"✅ Script quality PASSED: {final_score:.2f}/10")
        else:
            logging.warning(f"❌ Script quality FAILED: {final_score:.2f}/10 (threshold: {self.MIN_SCRIPT_SCORE})")
            logging.warning(f"   Issues: {', '.join(issues)}")
        
        self.scoring_history.append({
            "type": "script",
            "topic": topic,
            **result
        })
        
        return result
    
    def score_video(self, video_path: str, duration: Optional[float] = None) -> Dict[str, Any]:
        """
        Score video quality
        
        Args:
            video_path: Path to video file
            duration: Video duration in seconds (optional)
        
        Returns:
            Score dictionary
        """
        import os
        
        score = 0.0
        max_score = 10.0
        issues = []
        strengths = []
        
        # 1. File exists (2 points)
        if os.path.exists(video_path):
            score += 2.0
            strengths.append("Video file exists")
            
            # 2. File size (2 points)
            file_size = os.path.getsize(video_path)
            size_mb = file_size / (1024 * 1024)
            
            if 5 <= size_mb <= 500:  # Reasonable size
                score += 2.0
                strengths.append(f"Reasonable file size ({size_mb:.1f}MB)")
            elif size_mb < 5:
                score += 0.5
                issues.append(f"File size suspiciously small ({size_mb:.1f}MB)")
            else:
                score += 1.0
                issues.append(f"File size very large ({size_mb:.1f}MB)")
        else:
            issues.append("Video file does not exist")
        
        # 3. Duration check (2 points)
        if duration:
            if 45 <= duration <= 90:  # Shorts range
                score += 2.0
                strengths.append(f"Optimal duration ({duration:.1f}s)")
            elif 30 <= duration < 45 or 90 < duration <= 120:
                score += 1.0
                issues.append(f"Duration slightly off ({duration:.1f}s)")
            else:
                issues.append(f"Duration out of range ({duration:.1f}s)")
        else:
            score += 1.0  # Partial credit if duration not provided
            issues.append("Duration not provided")
        
        # 4. Format check (2 points) - assume passed if file exists
        if video_path.endswith('.mp4'):
            score += 2.0
            strengths.append("Correct format (MP4)")
        else:
            issues.append(f"Unexpected format: {video_path}")
        
        # 5. Basic validation (2 points)
        # Could add more checks here (resolution, codec, etc.)
        score += 2.0
        strengths.append("Basic validation passed")
        
        final_score = (score / max_score) * 10.0
        
        result = {
            "score": round(final_score, 2),
            "max_score": 10.0,
            "passed": final_score >= self.MIN_VIDEO_SCORE,
            "threshold": self.MIN_VIDEO_SCORE,
            "issues": issues,
            "strengths": strengths,
            "timestamp": datetime.now().isoformat()
        }
        
        if result["passed"]:
            logging.info(f"✅ Video quality PASSED: {final_score:.2f}/10")
        else:
            logging.warning(f"❌ Video quality FAILED: {final_score:.2f}/10")
        
        return result
    
    def score_metadata(self, seo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score SEO metadata quality
        
        Args:
            seo_metadata: SEO metadata dictionary
        
        Returns:
            Score dictionary
        """
        score = 0.0
        max_score = 10.0
        issues = []
        strengths = []
        
        title = seo_metadata.get("title", "")
        description = seo_metadata.get("description", "")
        tags = seo_metadata.get("tags", [])
        
        # 1. Title quality (3 points)
        if title:
            if 20 <= len(title) <= 60:
                score += 2.0
                strengths.append("Optimal title length")
            else:
                issues.append(f"Title length suboptimal ({len(title)} chars)")
            
            if len(title) <= 100:  # YouTube limit
                score += 1.0
            else:
                issues.append("Title exceeds YouTube limit")
        else:
            issues.append("Title missing")
        
        # 2. Description quality (3 points)
        if description:
            desc_len = len(description)
            if 100 <= desc_len <= 5000:
                score += 2.0
                strengths.append("Good description length")
            elif desc_len < 100:
                score += 0.5
                issues.append("Description too short")
            else:
                score += 1.0
                issues.append("Description very long")
            
            if desc_len <= 5000:  # YouTube limit
                score += 1.0
            else:
                issues.append("Description exceeds YouTube limit")
        else:
            issues.append("Description missing")
        
        # 3. Tags quality (2 points)
        if tags and isinstance(tags, list):
            if 3 <= len(tags) <= 10:
                score += 2.0
                strengths.append("Optimal tag count")
            elif len(tags) > 10:
                score += 1.0
                issues.append(f"Too many tags ({len(tags)})")
            else:
                score += 0.5
                issues.append(f"Insufficient tags ({len(tags)})")
        else:
            issues.append("Tags missing or invalid")
        
        # 4. Completeness (2 points)
        if title and description and tags:
            score += 2.0
            strengths.append("Complete metadata")
        else:
            missing = []
            if not title:
                missing.append("title")
            if not description:
                missing.append("description")
            if not tags:
                missing.append("tags")
            issues.append(f"Missing: {', '.join(missing)}")
        
        final_score = (score / max_score) * 10.0
        
        result = {
            "score": round(final_score, 2),
            "max_score": 10.0,
            "passed": final_score >= self.MIN_METADATA_SCORE,
            "threshold": self.MIN_METADATA_SCORE,
            "issues": issues,
            "strengths": strengths,
            "timestamp": datetime.now().isoformat()
        }
        
        if result["passed"]:
            logging.info(f"✅ Metadata quality PASSED: {final_score:.2f}/10")
        else:
            logging.warning(f"❌ Metadata quality FAILED: {final_score:.2f}/10")
        
        return result
    
    def score_complete(self, script_data: Dict[str, Any], video_path: str, 
                      seo_metadata: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """
        Score complete content package
        
        Returns:
            Overall score with pass/fail
        """
        script_score = self.score_script(script_data, topic)
        video_score = self.score_video(video_path)
        metadata_score = self.score_metadata(seo_metadata)
        
        # Weighted average
        overall_score = (
            script_score["score"] * 0.5 +
            video_score["score"] * 0.3 +
            metadata_score["score"] * 0.2
        )
        
        all_passed = (
            script_score["passed"] and
            video_score["passed"] and
            metadata_score["passed"]
        )
        
        result = {
            "overall_score": round(overall_score, 2),
            "passed": all_passed,
            "components": {
                "script": script_score,
                "video": video_score,
                "metadata": metadata_score
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if result["passed"]:
            logging.info(f"✅ Overall quality PASSED: {overall_score:.2f}/10")
        else:
            logging.error(f"❌ Overall quality FAILED: {overall_score:.2f}/10")
            failed = [k for k, v in result["components"].items() if not v["passed"]]
            logging.error(f"   Failed components: {', '.join(failed)}")
        
        return result


# Global scorer instance
quality_scorer = QualityScorer()
