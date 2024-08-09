class GlobalParameters:
    inflation_rate: int = 0.03

    # tax brackets (percentage, floor/bottom value of bracket)
    individual_tax_brackets: list[tuple[int, int]] = [(0.10, 0), (0.12, 11_001), (0.22, 44_726), (0.24, 95_376), (0.32, 182_101), (0.35, 231_251), (0.37, 578_126)] # (percent, bottom value)
    standard_tax_deduction: int = 13_850
    joint_tax_deduction: int = 27_700
    
    social_security_max_taxable: int = 160_200
    social_security_tax_percent: int = 0.062

    medicare_high_earner_tax = 0.09
    medicare_high_earner_salary_individual = 200_000
    medicare_high_earner_salary_joint = 250_000
    medicare_tax = 0.0145 # different if you are self-employed
