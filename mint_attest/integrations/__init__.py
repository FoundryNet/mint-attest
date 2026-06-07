"""Framework integrations for mint-attest.

Each module wraps a MintClient in a framework's native hook/callback/tool pattern
so a developer adds ONE line to their existing agent and every task attests. The
frameworks are optional dependencies — these modules import them lazily and raise
a clear, install-hint error if the framework isn't present. Importing
`mint_attest` itself never imports any framework.
"""
