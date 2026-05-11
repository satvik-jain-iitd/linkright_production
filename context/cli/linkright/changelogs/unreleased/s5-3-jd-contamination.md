## [type: Fixed]
<!-- pr: TBD -->
- **S5.3 (JD keyword contamination fix):** step_07 now strips keywords absent from raw JD text via structural filter; extraction prompt updated with explicit negative instruction. Prevents resume-sourced terms from inflating JD-alignment scores.
