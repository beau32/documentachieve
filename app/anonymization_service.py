"""
PII Detection and Document Anonymization Service

Detects and anonymizes personally identifiable information in documents
using pattern matching and NER (Named Entity Recognition).
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PIIType(str, Enum):
    """Supported PII entity types"""
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    PERSON = "person"
    ORGANIZATION = "organization"


@dataclass
class PIIEntity:
    """Detected PII entity"""
    entity_type: PIIType
    text: str
    start: int
    end: int
    confidence: float = 1.0


class AnonymizationService:
    """Service for detecting and anonymizing PII in document content"""

    # Regex patterns for pattern-based detection
    PATTERNS = {
        PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        PIIType.PHONE: r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        PIIType.SSN: r'\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0{4})\d{4}\b',
        PIIType.CREDIT_CARD: r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,19}\b',
        PIIType.IP_ADDRESS: r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
    }

    # PII type to replacement mask mapping
    REDACTION_MAP = {
        PIIType.NAME: "[NAME]",
        PIIType.EMAIL: "[EMAIL]",
        PIIType.PHONE: "[PHONE]",
        PIIType.SSN: "[SSN]",
        PIIType.CREDIT_CARD: "[CREDIT_CARD]",
        PIIType.IP_ADDRESS: "[IP_ADDRESS]",
        PIIType.ADDRESS: "[ADDRESS]",
        PIIType.DATE_OF_BIRTH: "[DOB]",
        PIIType.PERSON: "[PERSON]",
        PIIType.ORGANIZATION: "[ORGANIZATION]",
    }

    def __init__(self):
        """Initialize anonymization service"""
        self.compiled_patterns = {
            pii_type: re.compile(pattern, re.IGNORECASE)
            for pii_type, pattern in self.PATTERNS.items()
        }

    def detect_piis(
        self,
        text: str,
        pii_types: Optional[List[PIIType]] = None
    ) -> List[PIIEntity]:
        """
        Detect PII entities in text using pattern matching

        Args:
            text: Text to analyze
            pii_types: Specific PII types to detect. If None, detects all.

        Returns:
            List of detected PII entities
        """
        if not text:
            return []

        types_to_detect = pii_types or list(PIIType)
        detected = []

        # Pattern-based detection
        for pii_type in types_to_detect:
            if pii_type not in self.compiled_patterns:
                continue

            pattern = self.compiled_patterns[pii_type]
            for match in pattern.finditer(text):
                entity = PIIEntity(
                    entity_type=pii_type,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95
                )
                detected.append(entity)

        # Simple heuristic-based detection for names and addresses
        if PIIType.NAME in types_to_detect or not pii_types:
            name_patterns = [
                r'\b(?:[A-Z][a-z]+\s+){1,2}[A-Z][a-z]+\b',  # "John Smith"
                r'\b(?:Mr|Ms|Mrs|Dr|Prof)\.\s+[A-Z][a-z]+\b',  # "Mr. Smith"
            ]
            for pattern_str in name_patterns:
                pattern = re.compile(pattern_str)
                for match in pattern.finditer(text):
                    # Avoid duplicates
                    if not any(d.start == match.start() and d.end == match.end() for d in detected):
                        entity = PIIEntity(
                            entity_type=PIIType.NAME,
                            text=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=0.70
                        )
                        detected.append(entity)

        # Sort by position
        detected.sort(key=lambda x: x.start)

        # Remove overlapping entities (keep highest confidence)
        return self._remove_overlaps(detected)

    def _remove_overlaps(self, entities: List[PIIEntity]) -> List[PIIEntity]:
        """Remove overlapping entities, keeping highest confidence ones"""
        if not entities:
            return []

        filtered = []
        for entity in entities:
            # Check if overlaps with any already added entity
            overlaps = False
            for existing in filtered:
                if self._overlaps(entity, existing):
                    overlaps = True
                    # Replace if new entity has higher confidence
                    if entity.confidence > existing.confidence:
                        filtered.remove(existing)
                        filtered.append(entity)
                    break

            if not overlaps:
                filtered.append(entity)

        return filtered

    @staticmethod
    def _overlaps(entity1: PIIEntity, entity2: PIIEntity) -> bool:
        """Check if two entities overlap"""
        return not (entity1.end <= entity2.start or entity1.start >= entity2.end)

    def anonymize(
        self,
        text: str,
        pii_types: Optional[List[PIIType]] = None,
        mask_mode: str = "redact"
    ) -> Tuple[str, List[Dict]]:
        """
        Anonymize PII in text

        Args:
            text: Text to anonymize
            pii_types: Specific PII types to anonymize. If None, anonymizes all detected.
            mask_mode: "redact" (replace with [TYPE]) or "remove" (delete the text)

        Returns:
            Tuple of (anonymized_text, list of anonymization operations)
        """
        entities = self.detect_piis(text, pii_types)

        if not entities:
            return text, []

        # Process entities in reverse order to maintain position accuracy
        anonymized_text = text
        operations = []

        for entity in reversed(entities):
            if mask_mode == "remove":
                replacement = ""
            else:  # redact
                replacement = self.REDACTION_MAP.get(entity.entity_type, "[REDACTED]")

            anonymized_text = (
                anonymized_text[:entity.start] +
                replacement +
                anonymized_text[entity.end:]
            )

            operations.append({
                "type": entity.entity_type,
                "original_text": entity.text,
                "replacement": replacement,
                "position": {"start": entity.start, "end": entity.end},
                "confidence": entity.confidence
            })

        # Reverse operations list to maintain chronological order
        operations.reverse()

        return anonymized_text, operations

    def get_summary(self, entities: List[PIIEntity]) -> Dict[str, int]:
        """
        Get summary statistics of detected PIIs

        Args:
            entities: List of detected PII entities

        Returns:
            Dictionary with PII type counts
        """
        summary = {}
        for entity in entities:
            pii_type = entity.entity_type
            summary[pii_type] = summary.get(pii_type, 0) + 1

        return summary


# Singleton instance
_anonymization_service: Optional[AnonymizationService] = None


def get_anonymization_service() -> AnonymizationService:
    """Get or create anonymization service singleton"""
    global _anonymization_service
    if _anonymization_service is None:
        _anonymization_service = AnonymizationService()
    return _anonymization_service
