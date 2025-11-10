from typing import List, Dict

from services.extraction import extract_health_plans as llm_extract_plans


def extract_health_plans(text_content: str, district_name: str) -> List[Dict]:
    """
    Extract health insurance plans from transparency page content.
    
    Args:
        text_content: Parsed text from HTML or PDF
        district_name: District name for context
    
    Returns:
        List of plan dicts:
        [
            {
                'plan_name': str,
                'provider': str,
                'plan_type': str,
                'coverage_details': str | None,
                'source_url': str | None,
                'is_empty': bool
            },
            ...
        ]
    """
    print(f"\n[HEALTH PLAN EXTRACTION] Extracting plans for {district_name}")
    print(f"[HEALTH PLAN EXTRACTION] Content length: {len(text_content)} chars")
    
    _empty_result = lambda reason: [{
        'plan_name': None, 'provider': None, 'plan_type': None,
        'coverage_details': None, 'source_url': None,
        'is_empty': True, 'reasoning': reason
    }]

    # Quick validation: empty content
    if len(text_content.strip()) < 100:
        print("[HEALTH PLAN EXTRACTION] Content too short")
        return _empty_result('Content too short (less than 100 characters)')
    
    # Call LLM extraction service
    try:
        result = llm_extract_plans(text_content, district_name)

        # Extract plans and reasoning from Pydantic model
        plans = [plan.model_dump() for plan in result.plans]
        reasoning = result.reasoning

        print(f"[HEALTH PLAN EXTRACTION] LLM returned {len(plans)} plans")
        if reasoning:
            print(f"[HEALTH PLAN EXTRACTION] LLM reasoning: {reasoning[:200]}...")

        # Validate and clean results
        validated_plans = [_validate_plan(plan) for plan in plans]

        # Print valid plans
        [print(f"[HEALTH PLAN EXTRACTION]   ✓ {p['plan_name']} ({p['provider']}) - {p['plan_type']}"
               f"{' → ' + p['source_url'] if p['source_url'] else ''}")
         for p in validated_plans if not p['is_empty']]

        # If no valid plans found, return empty result
        if not any(not p['is_empty'] for p in validated_plans):
            print("[HEALTH PLAN EXTRACTION] No valid plans extracted")
            return _empty_result(reasoning or 'No health insurance plans found in content')

        return validated_plans

    except Exception as e:
        print(f"[HEALTH PLAN EXTRACTION] Extraction failed: {str(e)}")
        return _empty_result(f'LLM extraction failed: {str(e)}')


def _validate_plan(plan: Dict) -> Dict:
    """
    Validate and clean a single plan result.
    
    Args:
        plan: Raw plan dict from LLM
    
    Returns:
        Validated plan dict
    """
    # Check if marked as empty
    is_empty = plan.get('is_empty', False)
    
    # Extract fields
    plan_name = plan.get('plan_name')
    provider = plan.get('provider')
    plan_type = plan.get('plan_type')
    coverage_details = plan.get('coverage_details')
    source_url = plan.get('source_url')
    reasoning = plan.get('reasoning', '')
    
    # If any required field is missing, mark as empty
    if not is_empty and (not plan_name or not provider or not plan_type):
        is_empty = True
        reasoning = 'Missing required fields (plan_name, provider, or plan_type)'
    
    # Standardize provider names
    if provider:
        provider = _standardize_provider_name(provider)
    
    # Standardize plan type
    if plan_type:
        plan_type = _standardize_plan_type(plan_type)
    
    # Clean source URL
    if source_url and isinstance(source_url, str):
        source_url = source_url.strip()
        # Basic validation - must start with http/https
        if not source_url.startswith(('http://', 'https://')):
            source_url = None
    
    return {
        'plan_name': plan_name,
        'provider': provider,
        'plan_type': plan_type,
        'coverage_details': coverage_details,
        'source_url': source_url,
        'is_empty': is_empty,
        'reasoning': reasoning
    }


def _standardize_provider_name(provider: str) -> str:
    """
    Standardize insurance provider names.
    
    Args:
        provider: Raw provider name
    
    Returns:
        Standardized provider name
    """
    provider_lower = provider.lower()
    
    # MESSA variations
    if 'messa' in provider_lower:
        return 'MESSA'
    
    # Blue Cross Blue Shield variations
    if 'blue cross' in provider_lower or 'bcbs' in provider_lower or 'bcbsm' in provider_lower:
        return 'Blue Cross Blue Shield'
    
    # Priority Health
    if 'priority' in provider_lower and 'health' in provider_lower:
        return 'Priority Health'
    
    # HAP (Health Alliance Plan)
    if provider_lower in ['hap', 'health alliance plan']:
        return 'HAP'
    
    # Aetna
    if 'aetna' in provider_lower:
        return 'Aetna'
    
    # UnitedHealthcare
    if 'united' in provider_lower or 'uhc' in provider_lower:
        return 'UnitedHealthcare'
    
    # MPSERS (Michigan Public School Employees Retirement System)
    if 'mpsers' in provider_lower:
        return 'MPSERS'
    
    # Return original if no match
    return provider.strip()


def _standardize_plan_type(plan_type: str) -> str:
    """
    Standardize plan type names.
    
    Args:
        plan_type: Raw plan type
    
    Returns:
        Standardized plan type
    """
    plan_type_lower = plan_type.lower()
    
    if 'medical' in plan_type_lower or 'health' in plan_type_lower:
        return 'Medical'
    elif 'dental' in plan_type_lower:
        return 'Dental'
    elif 'vision' in plan_type_lower:
        return 'Vision'
    elif 'disability' in plan_type_lower:
        return 'Disability'
    elif 'life' in plan_type_lower:
        return 'Life Insurance'
    elif 'long-term care' in plan_type_lower or 'ltc' in plan_type_lower:
        return 'Long-Term Care'
    
    # Return original if no match
    return plan_type.strip()