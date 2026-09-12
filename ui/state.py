import json
import os
from typing import List

from utils.globals import GlobalParameters
from utils.parameters import Person
from utils.parse_parameters import generate_default_parameters, parse_parameters
from utils.schemas import ParametersSchema, PersonSchema


class AppState:
    def __init__(self, config_path: str = "config/parameters.json"):
        self.config_path = config_path
        self.raw_data = self.load_raw_data()
        self.parameters_schema = ParametersSchema.model_validate(self.raw_data)
        self.current_year = str(self.parameters_schema.CurrentYear)
        if self.current_year not in self.parameters_schema.years:
            self.current_year = sorted(list(self.parameters_schema.years.keys()))[-1]
        self.person_schema: PersonSchema = self.parameters_schema.years[
            self.current_year
        ].Person
        self.user: Person
        self.config: GlobalParameters
        self.user, self.config = parse_parameters(
            year=int(self.current_year), parameters_path=self.config_path
        )

    def get_available_years(self) -> List[str]:
        return sorted(list(self.parameters_schema.years.keys()))

    def load_raw_data(self) -> dict:
        if (
            not os.path.exists(self.config_path)
            or os.path.getsize(self.config_path) == 0
        ):
            return generate_default_parameters(self.config_path)
        with open(self.config_path, "r") as f:
            return json.load(f)

    def set_year(self, year_str: str):
        self.current_year = year_str
        self.parameters_schema.CurrentYear = int(year_str)
        self.person_schema = self.parameters_schema.years[self.current_year].Person
        self.user, self.config = parse_parameters(
            year=int(self.current_year), parameters_path=self.config_path
        )

    def save_raw_data(self):
        self.parameters_schema.years[self.current_year].Person = self.person_schema
        self.parameters_schema.CurrentYear = int(self.current_year)
        dumped = self.parameters_schema.model_dump(mode="json")
        out = {"CurrentYear": dumped["CurrentYear"]}
        for year_k, year_v in dumped.get("years", {}).items():
            out[year_k] = year_v
        with open(self.config_path, "w") as f:
            json.dump(out, f, indent=4)
        self.user, self.config = parse_parameters(
            year=int(self.current_year), parameters_path=self.config_path
        )

    def rename_account(self, old_name: str, new_name: str) -> bool:
        if old_name not in self.person_schema.Accounts:
            return False
        new_name_stripped = new_name.strip()
        if not new_name_stripped:
            return False
        if new_name_stripped == old_name:
            return True
        if new_name_stripped in self.person_schema.Accounts:
            return False

        new_accounts = {}
        for k, v in self.person_schema.Accounts.items():
            if k == old_name:
                new_accounts[new_name_stripped] = v
            else:
                new_accounts[k] = v
        self.person_schema.Accounts = new_accounts
        return True
