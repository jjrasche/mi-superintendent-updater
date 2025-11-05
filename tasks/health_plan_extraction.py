from typing import List, Dict

from utils.llm import build_health_plan_extraction_prompt, call_llm


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
                'is_empty': bool
            },
            ...
        ]
    """
    print(f"\n[HEALTH PLAN EXTRACTION] Extracting plans for {district_name}")
    print(f"[HEALTH PLAN EXTRACTION] Content length: {len(text_content)} chars")
    
    # Quick validation: empty content
    if len(text_content.strip()) < 100:
        print("[HEALTH PLAN EXTRACTION] Content too short")
        return [{
            'plan_name': None,
            'provider': None,
            'plan_type': None,
            'coverage_details': None,
            'is_empty': True,
            'reasoning': 'Content too short (less than 100 characters)'
        }]
    
    # Build prompts and call LLM
    system_prompt, user_prompt = build_health_plan_extraction_prompt(text_content, district_name)
    
    try:
        result = call_llm(system_prompt, user_prompt)
        
        # LLM should return {'plans': [...], 'reasoning': '...'}
        plans = result.get('plans', [])
        reasoning = result.get('reasoning', '')
        
        print(f"[HEALTH PLAN EXTRACTION] LLM returned {len(plans)} plans")
        if reasoning:
            print(f"[HEALTH PLAN EXTRACTION] LLM reasoning: {reasoning[:200]}...")
        
        # Validate and clean results
        validated_plans = []
        for plan in plans:
            validated_plan = _validate_plan(plan)
            validated_plans.append(validated_plan)
            
            if not validated_plan['is_empty']:
                print(f"[HEALTH PLAN EXTRACTION]   ✓ {validated_plan['plan_name']} "
                      f"({validated_plan['provider']}) - {validated_plan['plan_type']}")
        
        # If no valid plans found, return empty result
        if not any(not p['is_empty'] for p in validated_plans):
            print("[HEALTH PLAN EXTRACTION] No valid plans extracted")
            return [{
                'plan_name': None,
                'provider': None,
                'plan_type': None,
                'coverage_details': None,
                'is_empty': True,
                'reasoning': reasoning or 'No health insurance plans found in content'
            }]
        
        return validated_plans
        
    except Exception as e:
        print(f"[HEALTH PLAN EXTRACTION] Extraction failed: {str(e)}")
        return [{
            'plan_name': None,
            'provider': None,
            'plan_type': None,
            'coverage_details': None,
            'is_empty': True,
            'reasoning': f'LLM extraction failed: {str(e)}'
        }]


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
    
    return {
        'plan_name': plan_name,
        'provider': provider,
        'plan_type': plan_type,
        'coverage_details': coverage_details,
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