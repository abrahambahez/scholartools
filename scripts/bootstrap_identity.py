"""Bootstrap a peer identity for scholartools sync.

Usage:
    # First researcher (admin):
    uv run python scripts/bootstrap_identity.py \
        --peer-id sabhz --device-id laptop --role admin

    # Additional researcher (contributor):
    uv run python scripts/bootstrap_identity.py --peer-id alice --device-id laptop
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap scholartools peer identity")
    parser.add_argument(
        "--peer-id", required=True, help="Your stable researcher handle"
    )
    parser.add_argument("--device-id", required=True, help="This machine's identifier")
    parser.add_argument(
        "--role",
        choices=["admin", "contributor"],
        default="contributor",
        help="Role for this peer (admin = first researcher; contributor = additional)",
    )
    args = parser.parse_args()

    import scholartools as st

    result = st.peer_init(args.peer_id, args.device_id)
    if result.error and "already exists" not in result.error:
        print(f"peer init failed: {result.error}")
        sys.exit(1)
    if result.error:
        print("keypair already exists — skipping key generation")
    else:
        print(f"keypair created  public_key={result.identity.public_key}")

    peer_block = f'{{"peer_id": "{args.peer_id}", "device_id": "{args.device_id}"}}'
    print(f'\nAdd to config.json "peer" block:\n  "peer": {peer_block}')

    if args.role == "admin":
        reg = st.peer_register_self()
        if not reg.ok:
            print(f"peer_register_self failed: {reg.error}")
            sys.exit(1)
        print(f"registered {args.peer_id}/{args.device_id} as admin in peer directory")
    else:
        import base64

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        from scholartools.config import CONFIG_PATH

        key_path = CONFIG_PATH.parent / "keys" / args.peer_id / f"{args.device_id}.key"
        priv = Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
        pub = (
            base64.urlsafe_b64encode(priv.public_key().public_bytes_raw())
            .rstrip(b"=")
            .decode()
        )
        print(f"\nShare this public key with your admin to register you:\n  {pub}")


if __name__ == "__main__":
    main()
