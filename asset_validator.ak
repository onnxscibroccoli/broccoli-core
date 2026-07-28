// asset_validator.ak - Core PoV Asset State Machine (Aiken)

use aiken/transaction.{ScriptContext}
use aiken/list

type AssetDatum { ... } // as defined in V1.2

validator asset_state_machine(datum: AssetDatum, redeemer: Redeemer, ctx: ScriptContext) {
  // Transition logic here
  when redeemer is Transfer(new_owner) {
    // signature checks, atomic spend
  }
  // ... other cases
}
