# Hermes hardening assessment template

## 1. Mandate

- **Mode:** ASSESS / PLAN / APPLY / VERIFY
- **Target:**
- **Active profile / Hermes home:**
- **Evidence workspace:**
- **Declared runtime-write locations:**
- **Owner:**
- **Authorized action class:**
- **Allowed network reads:**
- **Allowed persistence / evidence writes:**
- **Explicit exclusions:**
- **Assessment timestamp:**
- **Hermes version / install method:**

## 2. Deployment statement

- **Purpose:**
- **Users and admins:**
- **Untrusted inputs:**
- **Data classes:**
- **Write-capable external systems:**
- **Unattended jobs:**
- **Network exposure:**
- **Recovery objective:**

## 3. Executive verdict

Choose one:

- fit for stated purpose;
- conditionally fit;
- not fit.

State what was actually tested, the most decision-relevant gaps, and the boundary of the verdict.

## 4. Evidence inventory

Record commands/sources and decision-relevant results without secret values.

| Evidence | Source/command | Result | Timestamp | Limitations |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 5. Control results

| Control | Status | Claim | Argument | Evidence | Gap / owner decision |
| --- | --- | --- | --- | --- | --- |
| HRD-… | pass/partial/fail/N/A/needs decision/unsupported |  |  |  |  |

## 6. Findings

For each finding:

### [Severity] Title

- **Class:** runtime defect / configuration gap / architecture gap / governance gap / accepted trade-off
- **Claim:**
- **Argument:**
- **Evidence:**
- **Consequence:**
- **Applicability:**
- **Recommended change:**
- **Rollback/recovery:**
- **Acceptance test:**
- **Residual risk:**

## 7. Proposed change set

This section is a plan, not authorization.

| Change | Target | Exact scope | Expected effect | Failure modes | Rollback | Requires fresh confirmation? |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## 8. Applied changes

Complete only in APPLY mode.

| Change | Previewed scope | Execution result | Independent read-back | Rollback state |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 9. Verification

- unauthorized gateway user:
- authorized gateway user:
- secret/PII scan:
- prompt-injection canary:
- private/cloud-metadata URL policy:
- tool/MCP allowlist:
- provider-side read-only denial:
- cron/one-shot dangerous-command denial:
- backup restore:
- gateway restart/recovery:
- critical integration canaries:

## 10. Residual risk and next decision

State precisely:

- what remains exposed;
- which controls are procedural rather than enforced;
- what was not testable;
- what decision the owner must make next;
- when this assessment expires (version, topology, or credential change).
