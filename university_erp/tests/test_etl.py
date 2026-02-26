"""
University ERP — Unit Tests for ETL Framework

Covers: Extractors, Transformers, Validators, Pipeline
"""

import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from python_core.etl.extractor import CSVExtractor, JSONExtractor
from python_core.etl.transformer import (
    StudentDataTransformer,
    GradeNormalizer,
    ChainedTransformer,
)
from python_core.etl.validator import SchemaValidator, StudentDataValidator
from python_core.etl.loader import CSVLoader, JSONLoader
from python_core.etl.pipeline import ETLPipeline
from python_core.utils.exceptions import ETLPipelineError


# ══════════════════════════════════════════════════════════════
#  EXTRACTOR TESTS
# ══════════════════════════════════════════════════════════════
class TestCSVExtractor(unittest.TestCase):

    def test_extract_from_string(self):
        csv_data = "first_name,last_name,email\nJohn,Doe,john@test.com\nJane,Smith,jane@test.com"
        ext = CSVExtractor()
        result = ext.extract(csv_data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["first_name"], "John")

    def test_extract_from_file(self):
        csv_data = "name,age\nAlice,20\nBob,22"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            f.flush()
            ext = CSVExtractor()
            result = ext.extract(f.name)
        os.unlink(f.name)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["name"], "Bob")

    def test_extract_invalid_source(self):
        ext = CSVExtractor()
        with self.assertRaises(ETLPipelineError):
            ext.extract(12345)


class TestJSONExtractor(unittest.TestCase):

    def test_extract_list_string(self):
        data = json.dumps([{"a": 1}, {"a": 2}])
        ext = JSONExtractor()
        result = ext.extract(data)
        self.assertEqual(len(result), 2)

    def test_extract_dict_with_key(self):
        data = json.dumps({"students": [{"name": "A"}]})
        ext = JSONExtractor(array_key="students")
        result = ext.extract(data)
        self.assertEqual(len(result), 1)

    def test_extract_from_file(self):
        records = [{"x": 1}, {"x": 2}, {"x": 3}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(records, f)
            f.flush()
            ext = JSONExtractor()
            result = ext.extract(f.name)
        os.unlink(f.name)
        self.assertEqual(len(result), 3)


# ══════════════════════════════════════════════════════════════
#  TRANSFORMER TESTS
# ══════════════════════════════════════════════════════════════
class TestStudentDataTransformer(unittest.TestCase):

    def test_transform_names(self):
        data = [{"first_name": "  john  ", "last_name": "doe", "email": "j@t.com",
                 "date_of_birth": "2000-01-01", "department_id": "CS", "gpa": "3.5"}]
        t = StudentDataTransformer()
        result = t.transform(data)
        self.assertEqual(result[0]["first_name"], "John")
        self.assertEqual(result[0]["last_name"], "Doe")

    def test_transform_email_lowercase(self):
        data = [{"first_name": "A", "last_name": "B", "email": "TEST@U.EDU",
                 "date_of_birth": "2000-01-01", "department_id": "CS"}]
        t = StudentDataTransformer()
        result = t.transform(data)
        self.assertEqual(result[0]["email"], "test@u.edu")

    def test_transform_gpa_clamp(self):
        data = [{"first_name": "A", "last_name": "B", "email": "a@b.com",
                 "date_of_birth": "2000-01-01", "department_id": "CS", "gpa": "5.0"}]
        t = StudentDataTransformer()
        result = t.transform(data)
        self.assertEqual(result[0]["gpa"], 4.0)

    def test_transform_date_formats(self):
        data = [{"first_name": "A", "last_name": "B", "email": "a@b.com",
                 "date_of_birth": "15/06/2000", "department_id": "CS"}]
        t = StudentDataTransformer()
        result = t.transform(data)
        self.assertEqual(result[0]["date_of_birth"], "2000-06-15")


class TestGradeNormalizer(unittest.TestCase):

    def test_score_to_grade(self):
        data = [{"student_id": "s1", "numeric_score": 95}]
        g = GradeNormalizer()
        result = g.transform(data)
        self.assertEqual(result[0]["grade"], "A")

    def test_failing_score(self):
        data = [{"student_id": "s1", "numeric_score": 45}]
        g = GradeNormalizer()
        result = g.transform(data)
        self.assertEqual(result[0]["grade"], "F")


class TestChainedTransformer(unittest.TestCase):

    def test_chain(self):
        data = [{"first_name": "john", "last_name": "doe", "email": "J@T.COM",
                 "date_of_birth": "2000-01-01", "department_id": "CS",
                 "numeric_score": 88}]
        chain = ChainedTransformer([StudentDataTransformer(), GradeNormalizer()])
        result = chain.transform(data)
        self.assertEqual(result[0]["first_name"], "John")
        self.assertEqual(result[0]["grade"], "B+")


# ══════════════════════════════════════════════════════════════
#  VALIDATOR TESTS
# ══════════════════════════════════════════════════════════════
class TestSchemaValidator(unittest.TestCase):

    def test_valid_records(self):
        schema = [
            {"field": "name", "type": "str", "required": True},
            {"field": "age", "type": "int", "min": 0, "max": 150},
        ]
        data = [{"name": "Alice", "age": 25}]
        v = SchemaValidator(schema)
        result = v.validate(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.valid_records), 1)

    def test_missing_required(self):
        schema = [{"field": "name", "type": "str", "required": True}]
        data = [{"name": ""}]
        v = SchemaValidator(schema)
        result = v.validate(data)
        self.assertFalse(result.is_valid)

    def test_range_violation(self):
        schema = [{"field": "gpa", "type": "float", "min": 0.0, "max": 4.0}]
        data = [{"gpa": 5.0}]
        v = SchemaValidator(schema)
        result = v.validate(data)
        self.assertFalse(result.is_valid)


class TestStudentDataValidator(unittest.TestCase):

    def _valid_record(self, **overrides):
        rec = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@test.edu",
            "date_of_birth": "2000-01-01",
            "gpa": 3.5,
            "department_id": "CS",
        }
        rec.update(overrides)
        return rec

    def test_valid_student(self):
        v = StudentDataValidator()
        result = v.validate([self._valid_record()])
        self.assertTrue(result.is_valid)

    def test_bad_email(self):
        v = StudentDataValidator()
        result = v.validate([self._valid_record(email="not-valid")])
        self.assertFalse(result.is_valid)

    def test_duplicate_emails(self):
        v = StudentDataValidator()
        r1 = self._valid_record(email="same@test.edu")
        r2 = self._valid_record(email="same@test.edu", first_name="Jane")
        result = v.validate([r1, r2])
        self.assertEqual(len(result.invalid_records), 1)

    def test_underage(self):
        v = StudentDataValidator()
        from datetime import date, timedelta
        too_young = (date.today() - timedelta(days=365 * 10)).isoformat()
        result = v.validate([self._valid_record(date_of_birth=too_young)])
        self.assertFalse(result.is_valid)

    def test_gpa_out_of_range(self):
        v = StudentDataValidator()
        result = v.validate([self._valid_record(gpa=5.0)])
        self.assertFalse(result.is_valid)


# ══════════════════════════════════════════════════════════════
#  LOADER TESTS
# ══════════════════════════════════════════════════════════════
class TestCSVLoader(unittest.TestCase):

    def test_load_to_file(self):
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        loader = CSVLoader()
        count = loader.load(data, path)
        self.assertEqual(count, 2)
        self.assertTrue(os.path.isfile(path))
        os.unlink(path)


class TestJSONLoader(unittest.TestCase):

    def test_load_to_file(self):
        data = [{"x": 1}, {"x": 2}]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        loader = JSONLoader()
        count = loader.load(data, path)
        self.assertEqual(count, 2)
        with open(path) as f:
            loaded = json.load(f)
        self.assertEqual(len(loaded), 2)
        os.unlink(path)


# ══════════════════════════════════════════════════════════════
#  PIPELINE INTEGRATION TEST
# ══════════════════════════════════════════════════════════════
class TestETLPipeline(unittest.TestCase):

    def test_full_pipeline(self):
        """End-to-end: CSV → Transform → Validate → JSON file."""
        csv_input = (
            "first_name,last_name,email,date_of_birth,department_id,gpa\n"
            "john,doe,john@test.edu,2000-01-01,CS,3.5\n"
            "jane,smith,jane@test.edu,2001-06-15,EE,2.8\n"
            "bad,,invalid-email,9999-01-01,, -1\n"
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name

        pipeline = ETLPipeline(
            extractor=CSVExtractor(),
            transformer=StudentDataTransformer(),
            validator=StudentDataValidator(),
            loader=JSONLoader(),
        )
        result = pipeline.run(csv_input, out_path, skip_invalid=True)

        self.assertEqual(result.extracted, 3)
        self.assertGreaterEqual(result.valid, 1)
        self.assertGreaterEqual(result.loaded, 1)
        self.assertTrue(os.path.isfile(out_path))
        os.unlink(out_path)


if __name__ == "__main__":
    unittest.main()
