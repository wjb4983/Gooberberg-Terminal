from __future__ import annotations

from pathlib import Path

CI_WORKFLOW = Path('.github/workflows/ci.yml')


def main() -> int:
    lines = CI_WORKFLOW.read_text(encoding='utf-8').splitlines()
    failures: list[str] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip().lower()
        if stripped.startswith('- name:') and 'test' in stripped:
            run_line = ''
            for probe in range(idx, min(idx + 6, len(lines))):
                candidate = lines[probe].strip()
                if candidate.startswith('run:'):
                    run_line = candidate
                    break
            if 'timeout ' not in run_line:
                failures.append(f'Line {idx}: step missing timeout wrapper -> {line.strip()}')

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print('All CI test jobs include timeout wrappers.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
