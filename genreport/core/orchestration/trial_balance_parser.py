"""
Trial Balance Parser - Module 1

Responsible for parsing and structuring trial balance data from WorksheetAnalysis.
Uses DSPy to classify accounts into categories (assets, liabilities, equity, revenue, expenses).

Author: GenReport Team
Date: 2025-10-25
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID
import dspy


class TrialBalanceAccount(BaseModel):
    """Structured representation of a single trial balance account."""

    code: str = Field(..., description="Account code (e.g., '1100', '4000')")
    name: str = Field(..., description="Account name (e.g., 'Cash and bank', 'Revenue')")
    balance: float = Field(..., description="Account balance")
    debit_credit: str = Field(..., description="'DR' or 'CR'")
    account_type: str = Field(
        ...,
        description="One of: asset, liability, equity, revenue, expense"
    )
    category: str = Field(
        ...,
        description="Specific category (e.g., 'current_asset', 'non_current_liability', 'operating_expense')"
    )
    is_material: bool = Field(
        default=False,
        description="Whether this account is material for disclosure purposes"
    )


class StructuredTrialBalance(BaseModel):
    """Fully structured and classified trial balance."""

    total_accounts: int = Field(..., description="Total number of accounts")
    total_assets: float = Field(default=0.0, description="Sum of all asset accounts")
    total_liabilities: float = Field(default=0.0, description="Sum of all liability accounts")
    total_equity: float = Field(default=0.0, description="Sum of all equity accounts")
    total_revenue: float = Field(default=0.0, description="Sum of all revenue accounts")
    total_expenses: float = Field(default=0.0, description="Sum of all expense accounts")

    accounts: List[TrialBalanceAccount] = Field(
        default_factory=list,
        description="All trial balance accounts with classifications"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (project_id, tenant_id, etc.)"
    )


class AccountClassificationSignature(dspy.Signature):
    """
    Classify a trial balance account into type and category.

    Given an account code and name, determine:
    1. Account type (asset/liability/equity/revenue/expense)
    2. Specific category (e.g., current_asset, operating_expense)
    """

    account_code: str = dspy.InputField(description="Account code (e.g., '1100', '4000')")
    account_name: str = dspy.InputField(description="Account name (e.g., 'Cash and bank', 'Revenue')")
    debit_credit: str = dspy.InputField(description="'DR' or 'CR' indicator")

    account_type: str = dspy.OutputField(
        description="One of: asset, liability, equity, revenue, expense"
    )
    category: str = dspy.OutputField(
        description="Specific category like 'current_asset', 'non_current_liability', 'cost_of_sales', etc."
    )
    reasoning: str = dspy.OutputField(
        description="Brief explanation of classification reasoning"
    )


class MaterialityAssessmentSignature(dspy.Signature):
    """
    Assess whether an account is material for disclosure purposes.

    Considers account balance relative to total assets and jurisdiction-specific
    materiality thresholds.
    """

    account_code: str = dspy.InputField(description="Account code")
    account_name: str = dspy.InputField(description="Account name")
    account_balance: float = dspy.InputField(description="Account balance")
    total_assets: float = dspy.InputField(description="Total assets for materiality comparison")
    jurisdiction: str = dspy.InputField(description="Jurisdiction (HK/SG/AU)")

    is_material: bool = dspy.OutputField(
        description="True if account requires disclosure"
    )
    materiality_percentage: float = dspy.OutputField(
        description="Account balance as percentage of total assets"
    )
    reasoning: str = dspy.OutputField(
        description="Explanation of materiality assessment"
    )


class DSPyTrialBalanceParser:
    """
    DSPy-based trial balance parser.

    Parses raw trial balance data and uses DSPy modules to:
    1. Classify each account into type and category
    2. Assess materiality
    3. Structure into StructuredTrialBalance format
    """

    def __init__(self, lm: Optional[dspy.LM] = None):
        """
        Initialize parser with LLM.

        Args:
            lm: DSPy language model (defaults to configured model)
        """
        if lm:
            dspy.configure(lm=lm)

        self.classifier = dspy.ChainOfThought(AccountClassificationSignature)
        self.materiality_assessor = dspy.ChainOfThought(MaterialityAssessmentSignature)

    def parse(
        self,
        raw_trial_balance: List[Dict[str, Any]],
        jurisdiction: str,
        tenant_id: UUID,
        project_id: int,
    ) -> StructuredTrialBalance:
        """
        Parse and classify raw trial balance data.

        Args:
            raw_trial_balance: List of dicts with keys: code, name, balance, debit_credit
            jurisdiction: Jurisdiction code (HK/SG/AU)
            tenant_id: Tenant UUID for audit trail
            project_id: Project ID

        Returns:
            StructuredTrialBalance with all accounts classified
        """
        # First pass: Classify all accounts
        classified_accounts: List[TrialBalanceAccount] = []

        for account_data in raw_trial_balance:
            classification = self.classifier(
                account_code=account_data["code"],
                account_name=account_data["name"],
                debit_credit=account_data.get("debit_credit", "DR"),
            )

            classified_accounts.append(
                TrialBalanceAccount(
                    code=account_data["code"],
                    name=account_data["name"],
                    balance=float(account_data["balance"]),
                    debit_credit=account_data.get("debit_credit", "DR"),
                    account_type=classification.account_type,
                    category=classification.category,
                    is_material=False,  # Will be updated in second pass
                )
            )

        # Calculate totals
        total_assets = sum(
            acc.balance for acc in classified_accounts
            if acc.account_type == "asset"
        )
        total_liabilities = sum(
            acc.balance for acc in classified_accounts
            if acc.account_type == "liability"
        )
        total_equity = sum(
            acc.balance for acc in classified_accounts
            if acc.account_type == "equity"
        )
        total_revenue = sum(
            acc.balance for acc in classified_accounts
            if acc.account_type == "revenue"
        )
        total_expenses = sum(
            acc.balance for acc in classified_accounts
            if acc.account_type == "expense"
        )

        # Second pass: Assess materiality
        for account in classified_accounts:
            materiality_result = self.materiality_assessor(
                account_code=account.code,
                account_name=account.name,
                account_balance=account.balance,
                total_assets=total_assets,
                jurisdiction=jurisdiction,
            )

            account.is_material = materiality_result.is_material

        return StructuredTrialBalance(
            total_accounts=len(classified_accounts),
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            accounts=classified_accounts,
            metadata={
                "tenant_id": str(tenant_id),
                "project_id": project_id,
                "jurisdiction": jurisdiction,
            },
        )
