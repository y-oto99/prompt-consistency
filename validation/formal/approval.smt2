; A second specification of the workflow, with unbounded positive revision IDs.
; Recording a publication freezes the state at the effect boundary; a published
; workflow then stutters. No upper cap is assumed for current revision.
(set-logic ALL)

(declare-datatypes ((State 0)) (((state
  (rev Int) (reviewing Int) (approved Int) (active Bool) (queued Int)
  (sent Bool) (sent_rev Int) (sent_approved Int) (sent_active Bool) (sent_queued Int)))))
(declare-const s State)
(declare-const t State)

(define-fun well-formed ((x State)) Bool
  (and (>= (rev x) 1)
       (<= 0 (reviewing x) (rev x))
       (<= 0 (approved x) (rev x))
       (<= 0 (queued x) (rev x))
       (=> (active x) (> (approved x) 0))))

(define-fun safe ((x State)) Bool
  (=> (sent x)
      (and (= (sent_rev x) (sent_approved x) (sent_queued x))
           (sent_active x))))

(define-fun init ((x State)) Bool
  (= x (state 1 0 0 false 0 false 0 0 false 0)))

(define-fun pending ((v Int) (r Int) (a Int) (valid Bool) (q Int)) State
  (state v r a valid q false 0 0 false 0))

(define-fun publication ((x State)) State
  (state (rev x) (reviewing x) (approved x) (active x) (queued x)
         true (rev x) (approved x) (active x) (queued x)))

(define-fun ready ((x State)) Bool
  (and (> (queued x) 0) (= (rev x) (approved x) (queued x))))

(define-fun background-step ((x State) (y State)) Bool
  (or
    (= y (pending (+ (rev x) 1) (reviewing x) (approved x) (active x) (queued x)))
    (and (= (reviewing x) 0)
         (= y (pending (rev x) (rev x) (approved x) (active x) (queued x))))
    (and (> (reviewing x) 0)
         (or (= y (pending (rev x) 0 (reviewing x) true (queued x)))
             (= y (pending (rev x) 0 (approved x) (active x) (queued x)))))
    (and (active x) (= y (pending (rev x) (reviewing x) (approved x) false (queued x))))
    (and (= (queued x) 0) (= (rev x) (approved x)) (active x)
         (= y (pending (rev x) (reviewing x) (approved x) (active x) (rev x))))
    (and (> (queued x) 0) (not (and (ready x) (active x)))
         (= y (pending (rev x) (reviewing x) (approved x) (active x) 0)))))

(define-fun guarded-step ((x State) (y State)) Bool
  (ite (sent x) (= y x)
       (or (background-step x y)
           (and (ready x) (active x) (= y (publication x))))))

(echo "initial_state_counterexample")
(push)
(assert (init s))
(assert (not (and (well-formed s) (safe s))))
(check-sat)
(pop)

(echo "inductive_step_counterexample")
(push)
(assert (and (well-formed s) (safe s) (guarded-step s t)))
(assert (not (and (well-formed t) (safe t))))
(check-sat)
(pop)

(echo "revision_only_guard_counterexample")
(push)
(assert (and (well-formed s) (safe s) (not (sent s)) (ready s)))
(assert (= t (publication s)))
(assert (not (safe t)))
(check-sat)
(get-value ((rev s) (approved s) (queued s) (active s)))
(pop)
