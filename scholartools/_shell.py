import code

import scholartools


def main():
    code.interact(
        banner="scholartools shell — 'scholartools' and all public functions available",
        local={
            "scholartools": scholartools,
            "scht": scholartools,  # alias
            **{
                k: getattr(scholartools, k)
                for k in dir(scholartools)
                if not k.startswith("_")
            },
        },
    )
