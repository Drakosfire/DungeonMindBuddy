# Record the actual image proposal request size

ACTIVE · PRIME · serial successor to merged #2394, from 11505add6.
Own the Build proposal authorization receipt and its ordinary HTTP regression.
The live Bath House request stopped before writer dispatch because its image
encoding alone exceeded the old 256 KiB limit on a receipt's byte-count field.
Record the measured size and existing digest. The receipt holds neither request
bytes nor a transport policy. Exercise an actual >256 KiB image-bearing request
through the existing guarded SDK path. No UI, provider-policy or schema change.
Independently review, deliver the one-file API patch and continue the failed
Bath House turn to review.
