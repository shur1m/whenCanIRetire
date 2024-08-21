class GlobalParameters:
    inflation_rate: int = 0.03

    # federal tax brackets (percentage, floor/bottom value of bracket)
    fed_individual_tax_brackets: list[tuple[int, int]] = [(0.10, 0), (0.12, 11_601), (0.22, 47_151), (0.24, 100_526), (0.32, 191_951), (0.35, 243_726), (0.37, 609_351)] # (percent, bottom value)
    fed_joint_tax_brackets: list[tuple[int, int]] = [(0.10, 0), (0.12, 22_001), (0.22, 89_451), (0.24, 190_751), (0.32, 364_201), (0.35, 462_501), (0.37, 693_751)] # (percent, bottom value)
    standard_tax_deduction: int = 13_850
    joint_tax_deduction: int = 27_700

    # state tax brackets
    state_individual_tax_brackets: list[tuple[int, int]] = [(0.01, 0), (0.02, 10_412), (0.04, 24_684), (0.06, 38_959), (0.08, 54_081), (0.093, 68_350), (0.103, 349_137), (0.113, 418_961), (0.123, 698_271)]
    state_joint_tax_brackets: list[tuple[int, int]] = [(0.01, 0), (0.02, 20_824), (0.04, 49_368), (0.06, 77_918), (0.08, 108_162), (0.093, 136_700), (0.103, 698_274), (0.113, 837_922), (0.123, 1_396_542)]
    state_standard_tax_deduction: int = 5_363
    state_joint_tax_deduction: int = 10_726
    
    social_security_max_taxable: int = 160_200
    social_security_tax_percent: int = 0.062

    medicare_high_earner_tax = 0.09
    medicare_high_earner_salary_individual = 200_000
    medicare_high_earner_salary_joint = 250_000
    medicare_tax = 0.0145 # different if you are self-employed
