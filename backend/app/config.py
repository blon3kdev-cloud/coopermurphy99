"""Centralised, validated runtime config — read once at boot from environment."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 4000
    node_env: str = Field(default="development", alias="NODE_ENV")
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")

    database_url: str = Field(alias="DATABASE_URL")
    mongodb_db: Optional[str] = Field(default=None, alias="MONGODB_DB")
    internal_secret: str = Field(alias="INTERNAL_SECRET")

    admin_login: str = Field(default="", alias="ADMIN_LOGIN")
    admin_pin: str = Field(default="", alias="ADMIN_PIN")
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD")
    admin_pin_hash: str = Field(default="", alias="ADMIN_PIN_HASH")
    admin_password_hash: str = Field(default="", alias="ADMIN_PASSWORD_HASH")

    @property
    def admin_uses_hashes(self) -> bool:
        return bool(self.admin_pin_hash.strip() and self.admin_password_hash.strip())

    dev_login_code: str = Field(default="", alias="DEV_LOGIN_CODE")
    dev_username: str = Field(default="devuser", alias="DEV_USERNAME")

    chainlink_api_key: str = Field(default="", alias="CHAINLINK_API_KEY")
    chainlink_api_secret: str = Field(default="", alias="CHAINLINK_API_SECRET")
    chainlink_feed_id: str = Field(
        default="0x00030ab7d02fbba9c6304f98824524407b1f494741174320cfd17a2c22eec1de",
        alias="CHAINLINK_FEED_ID",
    )
    chainlink_ws_url: str = Field(
        default="wss://ws.testnet-dataengine.chain.link", alias="CHAINLINK_WS_URL"
    )

    odds_api_key: str = Field(default="", alias="ODDS_API_KEY")
    isports_api_key: str = Field(default="", alias="I_SPORTS_API_KEY")
    isports_odds_bookmaker: str = Field(default="betclic", alias="I_SPORTS_ODDS_BOOKMAKER")

    # Crypto payments (HD wallet + chain monitoring)
    payment_wallet_mnemonic: str = Field(default="", alias="PAYMENT_WALLET_MNEMONIC")
    payment_wallet_passphrase: str = Field(default="", alias="PAYMENT_WALLET_PASSPHRASE")
    master_btc_address: str = Field(default="", alias="MASTER_BTC_ADDRESS")
    master_eth_address: str = Field(default="", alias="MASTER_ETH_ADDRESS")
    master_solana_address: str = Field(default="", alias="MASTER_SOLANA_ADDRESS")
    master_usdc_eth_address: str = Field(default="", alias="MASTER_USDC_ETH_ADDRESS")
    master_usdc_solana_address: str = Field(
        default="", alias="MASTER_USDC_SOLANA_ADDRESS"
    )
    solana_derivation_path: str = Field(default="", alias="SOLANA_DERIVATION_PATH")
    eth_rpc_url: str = Field(
        default="https://ethereum.publicnode.com", alias="ETH_RPC_URL"
    )
    solana_rpc_url: str = Field(
        default="https://api.mainnet-beta.solana.com", alias="SOLANA_RPC_URL"
    )
    etherscan_api_key: str = Field(default="", alias="ETHERSCAN_API_KEY")
    usdc_eth_contract: str = Field(
        default="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", alias="USDC_ETH_CONTRACT"
    )
    usdc_solana_mint: str = Field(
        default="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", alias="USDC_SOLANA_MINT"
    )
    payment_poll_interval_sec: int = Field(default=15, alias="PAYMENT_POLL_INTERVAL_SEC")
    payment_timeout_min: int = Field(default=60, alias="PAYMENT_TIMEOUT_MIN")
    payments_enable_solana: bool = Field(default=False, alias="PAYMENTS_ENABLE_SOLANA")
    payment_auto_sweep: bool = Field(default=True, alias="PAYMENT_AUTO_SWEEP")
    # Min on-chain balance before sweeping a deposit address (collect until reached)
    sweep_min_sol: float = Field(default=0.0001, alias="SWEEP_MIN_SOL")
    sweep_min_eth: float = Field(default=0.0005, alias="SWEEP_MIN_ETH")
    sweep_min_btc: float = Field(default=0.00001, alias="SWEEP_MIN_BTC")
    sweep_min_usdc: float = Field(default=1.0, alias="SWEEP_MIN_USDC")
    sweep_poll_interval_sec: int = Field(default=120, alias="SWEEP_POLL_INTERVAL_SEC")

    daily_code_amount_pln: float = Field(default=10.0, alias="DAILY_CODE_AMOUNT_PLN")
    daily_code_max_uses: int = Field(default=500, alias="DAILY_CODE_MAX_USES")

    blik_upload_dir: str = Field(default="data/blik_uploads", alias="BLIK_UPLOAD_DIR")
    blik_verify_strict: bool = Field(default=True, alias="BLIK_VERIFY_STRICT")

    telegram_token: str = Field(default="", alias="TELEGRAM_TOKEN")
    discord_token: str = Field(default="", alias="DISCORD_TOKEN")

    image_host_allowlist: str = Field(default="", alias="IMAGE_HOST_ALLOWLIST")

    # When true, rate limits use CF-Connecting-IP / X-Forwarded-For (set behind nginx/Cloudflare).
    trusted_proxy: bool = Field(default=False, alias="TRUSTED_PROXY")

    @property
    def payments_enabled(self) -> bool:
        return bool(self.payment_wallet_mnemonic.strip())

    @property
    def payments_solana_enabled(self) -> bool:
        return self.payments_enable_solana

    @property
    def master_usdc_eth(self) -> str:
        """Sweep destination for ERC-20 USDC (defaults to MASTER_ETH_ADDRESS)."""
        return self.master_usdc_eth_address.strip() or self.master_eth_address.strip()

    @property
    def master_usdc_solana(self) -> str:
        """Sweep destination for SPL USDC (defaults to MASTER_SOLANA_ADDRESS)."""
        return (
            self.master_usdc_solana_address.strip()
            or self.master_solana_address.strip()
        )

    @property
    def allowed_origins(self) -> list[str]:
        raw = [s.strip() for s in self.frontend_origin.replace(",", " ").split() if s.strip()]
        out: set[str] = set(raw)
        for o in raw:
            if "://" not in o:
                continue
            scheme, host = o.split("://", 1)
            if host.startswith("www."):
                out.add(f"{scheme}://{host[4:]}")
            elif not any(host.startswith(p) for p in ("localhost", "127.")):
                out.add(f"{scheme}://www.{host}")
        return sorted(out)

    @property
    def is_development(self) -> bool:
        return self.node_env.lower() in ("development", "dev")

    @property
    def mongodb_database(self) -> str:
        """DB name: URL path > MONGODB_DB > dev (development) or prod (production)."""
        if self.mongodb_db:
            return self.mongodb_db
        return "dev" if self.is_development else "prod"

    @property
    def dev_login_enabled(self) -> bool:
        return self.is_development and bool(self.dev_login_code.strip())

    @property
    def use_chainlink(self) -> bool:
        return bool(self.chainlink_api_key and self.chainlink_api_secret)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
