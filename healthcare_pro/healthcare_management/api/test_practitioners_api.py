#!/usr/bin/env python3


import frappe
from healthcare_pro.healthcare_management.api.get_practitioners import (
    get_practitioners_with_specializations,
    get_practitioner_specializations,
    search_practitioners
)

@frappe.whitelist(allow_guest=True)
def test_api():
    """Test all practitioner API functions"""
    print("Testing Healthcare Practitioners API...")
    print("=" * 50)

    # Test 1: Get all practitioners
    print("\n1. Testing get_practitioners_with_specializations()...")
    try:
        practitioners = get_practitioners_with_specializations()
        if isinstance(practitioners, list):
            print(f"✓ Found {len(practitioners)} practitioners")
            if len(practitioners) > 0:
                print(f"  Sample practitioner: {practitioners[0].get('name', 'N/A')}")
                print(f"  Specialization: {practitioners[0].get('specialization', 'N/A')}")
        else:
            print(f"✗ Unexpected response type: {type(practitioners)}")
            print(f"  Response: {practitioners}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 2: Get specializations
    print("\n2. Testing get_practitioner_specializations()...")
    try:
        specializations = get_practitioner_specializations()
        if isinstance(specializations, list):
            print(f"✓ Found {len(specializations)} unique specializations")
            if len(specializations) > 0:
                print(f"  Specializations: {', '.join(specializations[:5])}")
        else:
            print(f"✗ Unexpected response: {specializations}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 3: Search practitioners
    print("\n3. Testing search_practitioners()...")
    try:
        results = search_practitioners(search_term="Dr")
        if isinstance(results, list):
            print(f"✓ Search returned {len(results)} practitioners")
        else:
            print(f"✗ Unexpected search response: {results}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 4: Check Healthcare Practitioner doctype directly
    print("\n4. Testing direct Healthcare Practitioner access...")
    try:
        count = frappe.db.count("Healthcare Practitioner")
        print(f"✓ Total Healthcare Practitioner records: {count}")

        if count > 0:
            sample = frappe.get_all("Healthcare Practitioner",
                                  fields=["name", "practitioner_name", "specialization"],
                                  limit=1)
            if sample:
                print(f"  Sample record: {sample[0]}")
    except Exception as e:
        print(f"✗ Error accessing Healthcare Practitioner: {e}")

    print("\n" + "=" * 50)
    print("Test complete!")

if __name__ == "__main__":
    test_api()