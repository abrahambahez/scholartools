"""Bootstrap the _admin signing keypair and a personal peer identity.

Usage:
    uv run python scripts/bootstrap_identity.py --peer-id sabhz --device-id laptop
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
    args = parser.parse_args()

    import scholartools as st
    from scholartools import PeerIdentity

    admin = st.peer_init("_admin", "_admin")
    if admin.error and "already exists" not in admin.error:
        print(f"admin init failed: {admin.error}")
        sys.exit(1)
    if admin.error:
        print("admin keypair already exists — skipping")
    else:
        print("admin keypair created")

    result = st.peer_init(args.peer_id, args.device_id)
    if result.error and "already exists" not in result.error:
        print(f"peer init failed: {result.error}")
        sys.exit(1)
    if result.error:
        print("peer keypair already exists — re-registering")
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
        identity = PeerIdentity(
            peer_id=args.peer_id, device_id=args.device_id, public_key=pub
        )
    else:
        print(f"peer keypair created  public_key={result.identity.public_key}")
        identity = result.identity

    reg = st.peer_register(identity)
    if reg.error:
        print(f"peer register failed: {reg.error}")
        sys.exit(1)
    print(f"peer registered: {reg.peer_id}")


if __name__ == "__main__":
    main()
