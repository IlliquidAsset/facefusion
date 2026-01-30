# Jurisdiction Risk Assessment: Synthetic Content in Adult Film

**Date**: 2026-01-30
**Purpose**: Assess legal risk of using AI face synthesis for adult content production with consenting performers.

---

## Federal Law (United States)

### TAKE IT DOWN Act (2025)
- **Signed**: May 19, 2025
- **Key provision**: Criminalizes distribution of nonconsensual intimate deepfakes
- **Criminal penalties**: Up to 2 years imprisonment (adults), 3 years (minors)
- **Platform requirement**: Must remove nonconsensual content within 48 hours (effective May 19, 2026)
- **Critical distinction**: The law targets **nonconsensual** distribution. Content created WITH consent of the depicted person is NOT prohibited by this law.

### Implication for WatserFace
The TAKE IT DOWN Act is focused on nonconsensual content. A product that requires documented consent from the depicted person (consent manifest system) operates within the law, provided:
1. Consent is genuine and documented
2. The depicted person authorized the specific use
3. The content is not distributed against the person's wishes

---

## State Laws (Selected High-Risk Jurisdictions)

| State | Law | Scope | Consent Exemption? |
|-------|-----|-------|-------------------|
| **California** | Penal Code 632.01 | Criminalizes creating/sharing sexually explicit deepfakes of a real person **without consent** | YES — consent appears to be a defense |
| **Virginia** | Criminalized non-consensual deepfake porn | Distribution without consent | YES — targets non-consensual |
| **New Jersey** | P.L. 2025, c. 40 | Civil and criminal penalties for deceptive media | YES — includes Fair Use exemptions |
| **Idaho** | HB 575 | Disclosure of explicit synthetic media without consent | YES — consent-gated |
| **Utah** | U.C.A. 76-5b-205 | Distribution of counterfeit intimate images | Unclear — may apply regardless of consent |

### Key Pattern
The overwhelming legislative trend targets **nonconsensual** creation and distribution. As of January 2026, no US state law explicitly prohibits the creation of synthetic intimate content with the **informed, documented consent** of the depicted person.

**However**: Laws are evolving rapidly (40 states introduced bills in 2024 alone). The legal landscape could shift.

---

## Risk Mitigation Strategy

### Minimum Viable Compliance
1. **Consent documentation**: Every output must include a machine-readable consent manifest (planned in Task 9)
2. **Identity verification**: The person in the consent record must match the identity embedding used
3. **Takedown capability**: Must be able to trace any output back to its consent record
4. **Age verification**: Must verify all depicted persons are 18+ (absolute requirement, no exceptions)

### Recommended Legal Actions
1. **Consult an IP/entertainment attorney** specializing in synthetic media law ($200-$500 consultation)
2. **Form a legal entity** (LLC) before any commercial activity to limit personal liability
3. **Draft consent agreements** reviewed by an attorney, covering:
   - Scope of permitted use
   - Duration of license
   - Revocation mechanism
   - Compensation terms
4. **Consider Terms of Service** that explicitly prohibit non-consensual use by end users

---

## Assessment

**Risk Level: MODERATE**

The legal framework as of January 2026 generally permits consensual synthetic intimate content. The primary risks are:
1. **Evolving legislation** — new laws could change the landscape
2. **Platform liability** — if end users misuse the tool (distribute without consent)
3. **Perception risk** — even legal activity may face social/banking/payment-processing resistance
4. **Utah/ambiguous states** — some jurisdictions may not clearly exempt consensual creation

The consent manifest system (Task 9) is not just a nice-to-have — it's the legal foundation of the business. Without documented consent, the product enters criminal liability territory in multiple jurisdictions.

---

## NOT Legal Advice

This document is a research summary, not legal counsel. The user should consult a licensed attorney before commercial launch.
