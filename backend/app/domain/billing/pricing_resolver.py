"""
Pricing Rule Resolver.

Responsible for determining the applicable pricing rule for a trip.
Follows priority:
1. Fleet Owner Specific Rule (Not yet impl, placeholder)
2. Global Active Rule
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from backend.app.models.pricing_rule import PricingRule


class PricingResolver:
    
    @staticmethod
    async def resolve_active_rule(db: AsyncSession) -> PricingRule:
        """
        Find the currently active global pricing rule.
        
        Raises:
            ValueError: If no active pricing rule is found.
        """
        now = datetime.utcnow()
        
        # Future: Add logic here to check for Fleet Owner specific overrides
        
        # Check global active rule
        query = select(PricingRule).where(
            PricingRule.is_active == True,
            PricingRule.effective_from <= now,
            (PricingRule.effective_until.is_(None) | (PricingRule.effective_until >= now))
        ).order_by(PricingRule.effective_from.desc()).limit(1)
        
        result = await db.execute(query)
        rule = result.scalar_one_or_none()
        
        if not rule:
            raise ValueError("No active pricing rule found. Cannot process billing.")
            
        return rule
