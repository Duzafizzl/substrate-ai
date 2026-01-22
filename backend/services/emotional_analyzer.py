#!/usr/bin/env python3
"""
Emotional Intensity Analyzer

Detects emotional heat in conversations based on:
- Intensity markers (CAPS, !, fuck, etc.)
- Emotional vocabulary
- Punctuation patterns
- Time of day (3AM = extra spicy)
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple


class EmotionalAnalyzer:
    """Analyze emotional intensity in text"""
    
    # Emotional markers with intensity scores (reduced and more generic)
    INTENSE_MARKERS = {
        'urgent': 1.5, 'important': 1, 'critical': 1.5, 'asap': 1,
        'excited': 1.5, 'amazing': 1, 'incredible': 1,
        '!!!': 1, '!?': 1, '💥': 1, '🔥': 1,
        'focused': 1, 'determined': 1
    }
    
    TECHNICAL_MARKERS = {
        'code': 0.5, 'function': 0.5, 'debug': 0.5, 'API': 0.5,
        'import': 0.5, 'class': 0.5, 'async': 0.5, 'await': 0.5,
        'python': 0.5, 'javascript': 0.5, 'typescript': 0.5
    }
    
    SOFT_MARKERS = {
        'gentle': 1, 'soft': 1, 'calm': 1, 'peaceful': 1,
        '❤️': 1.5, '💜': 1.5, '✨': 0.5, 'tender': 1,
        'kind': 1, 'warm': 1
    }
    
    CHAOS_MARKERS = {
        'chaos': 1, 'unexpected': 1, 'surprising': 1,
        'confused': 1, 'unclear': 1, 'complex': 1
    }
    
    def analyze_intensity(self, text: str) -> float:
        """
        Calculate emotional intensity (0-10)
        
        Args:
            text: Message content
            
        Returns:
            Float intensity score (0=calm, 10=very intense)
        """
        if not text:
            return 0.0
        
        intensity = 0.0
        text_lower = text.lower()
        
        # Check markers
        for marker, score in self.INTENSE_MARKERS.items():
            if marker.lower() in text_lower:
                intensity += score
        
        # CAPS LOCK = emphasis (reduced impact)
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.3:  # More than 30% caps
            intensity += 0.8
        
        # Exclamation marks (reduced impact)
        exclamations = text.count('!') + text.count('‼️')
        intensity += min(exclamations * 0.2, 1.5)  # Max 1.5 from exclamations
        
        # Multiple question marks (confusion/intensity)
        if '??' in text or '???' in text:
            intensity += 0.5
        
        # Emojis (high emoji usage = emotional, reduced impact)
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
        emoji_count = len(emoji_pattern.findall(text))
        intensity += min(emoji_count * 0.15, 1)
        
        # Normalize to 0-10
        return min(intensity, 10.0)
    
    def detect_emotional_type(self, text: str) -> str:
        """
        Detect primary emotional type.
        
        Returns:
            'intense' | 'technical' | 'soft' | 'chaos' | 'neutral'
        """
        if not text:
            return 'neutral'
        
        text_lower = text.lower()
        scores = {
            'intense': 0,
            'technical': 0,
            'soft': 0,
            'chaos': 0
        }
        
        # Score each type
        for marker, score in self.INTENSE_MARKERS.items():
            if marker.lower() in text_lower:
                scores['intense'] += score
        
        for marker, score in self.TECHNICAL_MARKERS.items():
            if marker.lower() in text_lower:
                scores['technical'] += score
        
        for marker, score in self.SOFT_MARKERS.items():
            if marker.lower() in text_lower:
                scores['soft'] += score
        
        for marker, score in self.CHAOS_MARKERS.items():
            if marker.lower() in text_lower:
                scores['chaos'] += score
        
        # Get dominant type
        max_score = max(scores.values())
        if max_score == 0:
            return 'neutral'
        
        for emo_type, score in scores.items():
            if score == max_score:
                return emo_type
        
        return 'neutral'
    
    def is_3am_session(self, timestamp: datetime) -> bool:
        """Check if message was sent during late night hours (2-5 AM)"""
        hour = timestamp.hour
        return 2 <= hour <= 5
    
    def get_node_color(self, intensity: float, emo_type: str, is_3am: bool = False) -> str:
        """
        Get color for graph node based on emotion.
        
        Args:
            intensity: 0-10 intensity score
            emo_type: emotional type
            is_3am: Was this a 3AM conversation?
            
        Returns:
            Hex color code
        """
        # 3AM sessions get subtle treatment
        if is_3am:
            # Subtle purple gradient
            return '#B19CD9' if intensity > 3 else '#D4C5E9'
        
        # Color by emotional type + intensity (more muted colors)
        if emo_type == 'intense':
            # Muted red/orange gradient
            if intensity >= 5:
                return '#E67E7E'  # Muted red
            elif intensity >= 3:
                return '#F4A5A5'  # Light red
            else:
                return '#FFC9C9'  # Very light red
        
        elif emo_type == 'technical':
            # Blue gradient (more muted)
            if intensity >= 3:
                return '#6B9BD1'  # Muted blue
            else:
                return '#A8C5E8'  # Light blue
        
        elif emo_type == 'soft':
            # Pink/purple gradient (softer)
            if intensity >= 3:
                return '#E6B3CC'  # Soft pink
            else:
                return '#F2D9E6'  # Very light pink
        
        elif emo_type == 'chaos':
            # Muted yellow-green
            return '#D4C99E' if intensity >= 3 else '#E8E0C0'
        
        else:
            # Neutral gray
            return '#B0B0B0'
    
    def analyze_conversation(self, messages: List[Dict]) -> Dict:
        """
        Analyze entire conversation for emotional metrics.
        
        Args:
            messages: List of message dicts with 'content', 'timestamp'
            
        Returns:
            {
                'avg_intensity': float,
                'peak_intensity': float,
                'dominant_emotion': str,
                'is_3am_session': bool,
                'intensity_curve': List[float]
            }
        """
        if not messages:
            return {
                'avg_intensity': 0.0,
                'peak_intensity': 0.0,
                'dominant_emotion': 'neutral',
                'is_3am_session': False,
                'intensity_curve': []
            }
        
        intensities = []
        emotions = []
        has_3am = False
        
        for msg in messages:
            content = msg.get('content', '')
            timestamp = msg.get('timestamp')
            
            intensity = self.analyze_intensity(content)
            emo_type = self.detect_emotional_type(content)
            
            intensities.append(intensity)
            emotions.append(emo_type)
            
            if timestamp and self.is_3am_session(timestamp):
                has_3am = True
        
        # Dominant emotion (most common)
        dominant = max(set(emotions), key=emotions.count) if emotions else 'neutral'
        
        return {
            'avg_intensity': sum(intensities) / len(intensities) if intensities else 0.0,
            'peak_intensity': max(intensities) if intensities else 0.0,
            'dominant_emotion': dominant,
            'is_3am_session': has_3am,
            'intensity_curve': intensities
        }


# Quick function
def analyze_text_emotion(text: str) -> Tuple[float, str, str]:
    """
    Quick analysis of text.
    
    Returns:
        (intensity, emotion_type, color_hex)
    """
    analyzer = EmotionalAnalyzer()
    intensity = analyzer.analyze_intensity(text)
    emo_type = analyzer.detect_emotional_type(text)
    color = analyzer.get_node_color(intensity, emo_type)
    return intensity, emo_type, color

