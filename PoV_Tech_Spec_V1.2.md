# Proof-of-Value (PoV) Asset Protocol Technical Specification V1.2

## Overview
The Proof-of-Value (PoV) protocol enables tokenized Real-World Assets (RWAs) on Cardano using the eUTXO model. Each asset is managed as an independent state machine.

## Core Components

### AssetDatum
```aiken
type AssetDatum {
  owner: PubKeyHash,              // Current controlling entity
  asset_id: ByteArray,            // Unique identifier (e.g., hash of legal docs + serial)
  value: Int,                     // Current appraised or nominal value in lovelace / base unit
  status: AssetStatus,            // Enum: Minted, Active, Locked, Transferred, Redeemed
  metadata_ref: Option<ByteArray>,// Reference to off-chain metadata / oracle commitments
  legal_wrapper: ByteArray,       // Series LLC / DAO identifier
  compliance_flags: List<ComplianceFlag>, // e.g., KYC level, jurisdiction tags
  last_valuation: Int,            // Timestamp of last oracle-updated valuation
  distribution_policy: ByteArray, // Hash of active distribution script
}
```

enum AssetStatus {
  Minted,
  Active,
  Locked,
  Transferred,
  Redeemed,
}

enum ComplianceFlag {
  KycLevel1,
  KycLevel2,
  JurisdictionUS,
  // ...
}
```

### asset_state_machine Validator
The core Aiken validator implements a finite state machine for each asset's eUTXO datum. Key transitions:

1. **Mint**: Create new datum with owner signature + legal proof commitment.
2. **Transfer**: Owner signs + new owner pubkey; atomic with payment.
3. **Value Update**: Oracle multi-sig signs new valuation (referenced in metadata_ref); atomic check against treasury.
4. **Distribution**: Trigger revenue share per policy script.
5. **Lock/Redeem**: Governance or compliance trigger.

All transitions are atomic: if any condition (balance, signatures, oracle validity) fails, the entire tx rolls back via eUTXO spending conditions.

## Legal Framework Mapping
- Series LLC to eUTXO states (1:1 mapping)
- RWA-DAO wrappers for governance

## Updates from V1.0
- Refined valuation and distribution engines
- Enhanced compliance integrations
