import sys

import loretools


def _read(args):
    result = loretools.read_reference(args.citekey, force=args.force)
    print(result.model_dump_json())
    if result.error is not None:
        sys.exit(1)


def register(sub):
    sub.add_argument("citekey")
    sub.add_argument("--force", action="store_true", default=False)
    sub.set_defaults(func=_read)
