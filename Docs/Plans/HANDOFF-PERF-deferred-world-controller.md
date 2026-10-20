# Defer unused World conversation code; retain activated owners

**Status:** COMPLETE. PR1497 merged as 76e370c79accb00410e6577e8cb1d786863dbc4b and accepted on 5202.
**Base:**f65e201efe9a22bfdc635c1afef99ffd7c5fd9ef (accepted1498); originalheldbase60cb4b4e44d0e86cbf71bbbac081c985154b61db. Existing checkout branch codex/defer-world-conversation-controller. Serial after1496. UI-only5202, no backend/data/dependency change.

## Capability and ownership

Fresh Index/candidate Ingest with no pending World work must not import the heavy World conversation controller. Explicit Plan/Play/Build surface context or existing pending recovery activates it. Once activated within the selected World owner, retain the same deferred child/component identity across subsequent route/visibility/context changes. Existing unavailable-Play hold still unmounts transport as required; clearing that hold follows current semantics. Existing World-keyed App provider remains sole World lifetime boundary. Providers/registry/controller transport/recovery/drafts/history/lastPlan/currentprops unchanged. No unload-on-close, replay, history polling or eager startup probe.

Use a lightweight conservative presence scan of current emitted localStorage keys for exact encoded World: Plan pending Ask (any document), pending new-conversation, pending Play/Build turn, and saved command-resolution marker. Key presence including malformed/empty bytes requests activation; the heavy controller alone validates or displays recovery errors. Do not read/parse story envelopes, remove bytes, infer accepted/terminal status or repair storage in the loader. Inaccessible storage conservatively activates validation. Cross-tab storage events for relevant keys, clear and inaccessible storage trigger rescan; same-tab new pending work already requires active controller. Initial check + effect rescan avoids render→listener gap. OtherWorld keys never activate currentWorld. A World change must reset activation, without using a stale lastPlan registration.

## Write lease

agentInteraction/WorldAgentConversation.tsx static value import replaced by module-scope deferredComponent; keep prop types type-only. Add small current-key presence helper/hook if needed and focused owner tests. Existing root host/provider/World keys and heavy WorldPlanAgentConversation source unchanged. Test-only dynamic loader mocks/fixtures; existing direct Plan/Play/Build integration expectations updated only for actual async loading if required, no compatibility path. This contract plus1496backwardssettlement. No editor/proposal semantics extraction, no generic deferred helper redesign or storage schema transition.

## Evidence and gate

Current accepted initialJS ~1.329MB. An in-memory static-edge-only build estimate suggests ~1.006MB (24%raw reduction); not productimplementation or acceptedresult. It still has36editor/prosemirrormodules, so do not claim editorfullysplit. The audit accidentally wrote localdist because write:false was specified at wrong config level; default5202 guard prevented adoption and1496exactsource rebuilt. Future audits use build:{write:false}.

Prove coldinactive import0; Plan/Play/Build activates; activated route/close retains same mountedcontroller/draft/currentprops; exactWorldreset; valid+malformed+empty recoverypresence andstorageerrors activate withoutwrite; irrelevantWorld/otherkeys noactivation; storageevent/clear/rescangap; pendingrecoveryhistory andunavailablePlay hold preserve existing behavior. Deferredloadfailure explicitretry and latestcontext/Worldfences, actualcurrenttransport recovery cohorts (knownbasefailures attributed). Inspect cumulative diff/chunkownership, actualTypeScript/build, independentexactheadreview, merge andnativepaired5202 entry/coldIndex +Plan/Play/Build transitions,17protectedresponses. Memory/latency limits honest; no target-laptop claim from buildbytes alone.

Rules next means user+Buddy cited lookup, using existing RulesLawyer/RulesIngestion design. Rulegraph experiments remain deferred until all four objectives delivered.

## Author findings and prerequisite hold

Bounded source loader implemented: both value uses share module-scope deferredtype, World-keyed scopedchild keeps activation/lastPlan isolated,256keypresencecap (overflow/inaccessible→conservativeactivation), no envelope reads/writes. Heavycontroller and registry APIs unchanged. Newowner21/21passes (12presence,6host,3existingdeferredhelper), including controlledunresolvedmodule/latestWorld/draftDOMretention/routeprops, directregistration, unavailablePlayexception. Test-controlledloader shares onlypendingimports to avoidVitestconcurrentmock recursion, thenreleasespendingpromise asnativeimportsdo; no producthelperchanges. Realintegration53pass/7fail anddirecthistory208pass/8fail, all15names/counts reproducedexactbase60cb4in samecheckoutwith finallyrestoration. ActualappTS/buildpass.

Candidate entryindex-5klxh-tU.js1,009,305raw/295,286encoded, controllerchunk254,020raw/66,676encoded. NativeunselectedIndex0controllerchunk. SelectedElderwyld has36storagekeys/18recoverymarkers, so rightlyloadscontroller;0inference. These records are not cleared. BrowserreportedusedJSheap~16.8MB onthishost, nonstandard/nonisolatedobservation; notRSS, comparativeRAMproof or8GBhardwareclaim.

Native fullAppPlan→Play→Plan drops temporaryunsentQAtext and remounts conversation. ReproducedonUNCHANGEDacceptedindex-BQBQggex.js too, confirming rootbaseline, not introducedlazybehavior. Originalcomposerrestoredexactlyinbothcases; noSend/providerdispatch,17protectedresponsesunchanged. CurrentSelectedWorldProvider keysverificationbyfullobjectselectors andeffectdependslocationSnapshot; loadingSelectedWorldAppreturnunmountsWorldregistry/controller on sameWorld routechange. Thuscomponenttests doNOTprove fullAppcontinuity. DeferPR mustremainheld untilseparatelyboundedrootWorld-lifetimeprerequisiteisreviewed/merged/adopted, thenrebaseandrepeatnativefullAppcontinuity. Screenshotsunavailable;DOM/metadatareceipts. Temporarytabs/HTMLremoved, default5202remains1496.

## Prerequisite settlement and reactivation

RootPR1498 reviewed in2cycles, mergedf65e201efe9a22bfdc635c1afef99ffd7c5fd9ef and accepted5202; exactnativeQAunsentPlan→Play→Plan nowretained, registry4→1,17protectedunchanged. This existingbranch rebased cleanly onto acceptedf65; Root currentbridge/save/clear gating retained in the World-keyedScopedhost. Heavycontroller/providerRegistry APIs byteunchanged relativetoacceptedbase. Rootsettlementincluded. Draft1497 no prior formal sourceapproval; newhead must receive independent source review, then native fullApp continuity and protected17 before its own merge/delivery claim. The older nativehold evidence above is history, not an active blocker after verified1498 settlement.

## Rebased author verification

On acceptedf65 root,7filecombined owner54/54PASS: loader/presence/helper21 and actualApp/selection/currentmanagedGraph/navigation33. Realcurrentconversation+history261pass/15sameknownbaseline failures; no newfailure. ActualappTypeScript/productionbuildpass. Sourceonlyscopehostimport/activation; acceptedrootedit/save/clear gating preserved; registry APIs/heavycontroller/transportsourceunchanged. Rebasedentryindex-C5WRhiOK.js1,010,642raw; controllerchunk254,020raw. Gzip/compressedcounts mustlabelcompressor or use nativeencoded receipt; previousgzip9manualcount is not networktransfer. Cumulativef65→head inspected/diffcheckclean. No defaultadoption yet; formal exactheadreview next, nativefullApp continuity/protected17 follow.

## Accepted settlement

Architecture Cycle 1 source APPROVE at 5e2528d76b8aef5cc8145604bb052b4256f71c70; independently 54/54 selected tests, Bugbot no findings. Exact accepted entry index-C5WRhiOK.js: 1,010,642 raw bytes, 295,557 native encoded bytes on cold Index. No World controller chunk on unselected Index; zero inference requests. Real Plan → Play → Plan retains exact temporary unsent draft; original restored, one registry read, zero inference. Existing recovery markers untouched. All 17 protected responses unchanged, API health OK. Prior UI assets retained; owned QA tabs and temporary trace HTML removed. Source maps/audit still identify editor dependencies through the eager reference renderer, addressed in a separate slice.
