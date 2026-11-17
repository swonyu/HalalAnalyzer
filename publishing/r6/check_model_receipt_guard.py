#!/usr/bin/env python3
"""Check only parsed boolean receipt predicates against actual and negative JSON.

This imports neither adapter and executes no model, native or release command.
"""
from pathlib import Path
import argparse
import ast
import copy
import json


def expressions(path, messages):
    tree = ast.parse(path.read_text())
    found = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'require' and len(node.args) == 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in messages):
            assert node.args[1].value not in found
            found[node.args[1].value] = compile(ast.Expression(node.args[0]), str(path), 'eval')
    assert set(found) == set(messages)
    return list(found.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-adapter', type=Path, required=True)
    parser.add_argument('--release-fragment', type=Path, required=True)
    parser.add_argument('--actual-result', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    native = expressions(args.native_adapter, [
        'Model checks did not report complete success',
        'Required Arabic-semicolon regressions are missing or duplicated'])
    release = expressions(args.release_fragment, [
        'Actual model stdout does not establish complete passing checks',
        'Required boundary regressions did not run exactly once'])
    required = [label + separator for separator in (';', '؛') for label in (
        'Separated entries cannot form an additive code: ',
        'Separated entries cannot form a multiword ingredient: ',
        'A qualifier in an earlier entry cannot suppress a direct term: ',
        'A qualifier in a later entry cannot suppress a direct term: ',
    )] + ['Arabic semicolons preserve valid within-entry terms and phrases']
    actual = json.loads(args.actual_result.read_text())['observed']
    assert actual['status'] == 'PASS' and actual['check_count'] == len(actual['checks']) == 211
    assert actual['checks'].count('Arabic sample preview contains exact inserted English text') == 3
    assert all(actual['checks'].count(label) == 1 for label in required)
    assert len(set(actual['checks'])) != len(actual['checks']), 'Historical failure must reproduce'
    cases = [('actual_211_with_three_existing_sample_labels', actual, True)]
    missing = copy.deepcopy(actual)
    missing['checks'].remove(required[0]); missing['check_count'] -= 1
    cases.append(('missing_required_boundary_check', missing, False))
    duplicate = copy.deepcopy(actual)
    duplicate['checks'].append(required[0]); duplicate['check_count'] += 1
    cases.append(('duplicate_required_boundary_check', duplicate, False))
    wrong_count = copy.deepcopy(actual); wrong_count['check_count'] += 1
    cases.append(('incorrect_declared_count', wrong_count, False))
    failed = copy.deepcopy(actual); failed['status'] = 'FAIL'
    cases.append(('failure_status', failed, False))
    malformed = copy.deepcopy(actual); malformed['checks'][0] = 42
    cases.append(('non_string_check_label', malformed, False))
    rows = []
    for name, result, expected in cases:
        scope = {'output': result, 'result': result, 'checks': result['checks'],
                 'boundary_checks': required, 'required': required,
                 'receipt': {'actual_result': result, 'required_boundary_check_count': 9}}
        builtins = {'all': all, 'len': len, 'str': str, 'list': list, 'isinstance': isinstance}
        observed = {}
        for label, predicates in [('native', native), ('release', release)]:
            observed[label] = all(eval(code, {'__builtins__': builtins, **scope}) for code in predicates)
            assert observed[label] is expected, (name, label, observed[label], expected)
        rows.append({'case': name, 'expected_acceptance': expected, 'actual': observed})
    record = {'status': 'PARSED_RECEIPT_PREDICATE_REGRESSIONS_PASS',
              'cases': rows, 'original_model_checks_observed': 211,
              'original_native_ui_result': 'NOT_RUN', 'native_command_executed_here': False,
              'release_adapter_imported_or_invoked': False,
              'scope': 'Boolean receipt conditions only; no model re-execution or native/release acceptance'}
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
