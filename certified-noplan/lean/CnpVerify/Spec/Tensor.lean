/-
CnpVerify.Spec.Tensor — reference semantics of coefficient tensors (L2: T2–T7 proved).

`Tensor.eval` is the real-valued polynomial function a tensor denotes. It is NONCOMPUTABLE and
is never run: it only appears in statements.

Method (L2). A tensor denotes a polynomial `toMv t : MvPolynomial (Fin n) ℚ` — the sum of its
monomials — and `eval t x = aeval x (toMv t)`. Each executable operation is characterised on
`toMv`: `support` lists the monomials of `t`, `ofTerms` sums the listed monomials that fit its
layout, and `add`, `scale`, `mul`, `padTo?`, `trim` follow. The lemmas T2–T7 are then the
corresponding facts about `MvPolynomial`.
-/
import Mathlib
import CnpVerify.Tensor
import CnpVerify.Spec.Index

namespace CnpVerify

namespace Tensor

variable {n : ℕ}

/-- The real number denoted by the tensor `t` at the point `x`:
`Σ_e coeff(e) · ∏ᵢ xᵢ^eᵢ`, the sum ranging over all exponent vectors `e ∈ {0..deg}ⁿ`. -/
noncomputable def eval (t : Tensor n) (x : Fin n → ℝ) : ℝ :=
  ∑ e : Fin n → Fin (t.deg + 1), (t.coeff (fun i => (e i).val) : ℝ) * ∏ i, x i ^ (e i).val

/-! ### Monomials and the polynomial of a layout -/

/-- The monomial `c · ∏ᵢ sᵢ^(f i)`. -/
noncomputable def mono (f : Fin n → ℕ) (c : ℚ) : MvPolynomial (Fin n) ℚ :=
  MvPolynomial.monomial (Finsupp.equivFunOnFinite.symm f) c

theorem mono_zero (f : Fin n → ℕ) : mono f 0 = 0 := by simp [mono]

theorem mono_add (f : Fin n → ℕ) (a b : ℚ) : mono f (a + b) = mono f a + mono f b := by
  simp [mono]

theorem mono_mul (f g : Fin n → ℕ) (a b : ℚ) :
    mono f a * mono g b = mono (fun i => f i + g i) (a * b) := by
  unfold mono
  rw [MvPolynomial.monomial_mul_monomial]
  congr 2
  ext i
  simp

theorem aeval_mono (x : Fin n → ℝ) (f : Fin n → ℕ) (c : ℚ) :
    MvPolynomial.aeval x (mono f c) = (c : ℝ) * ∏ i, x i ^ f i := by
  unfold mono
  rw [MvPolynomial.aeval_monomial, Finsupp.prod_fintype _ _ (by simp)]
  simp

/-- The polynomial denoted by the coefficient array `arr` read in the layout of degree `d`. -/
noncomputable def arrPoly (d : ℕ) (arr : Array ℚ) : MvPolynomial (Fin n) ℚ :=
  ∑ e : Fin n → Fin (d + 1),
    mono (fun i => (e i : ℕ)) (arr.getD (flatIndex (d + 1) fun i => (e i : ℕ)) 0)

/-- The polynomial with rational coefficients a tensor denotes. -/
noncomputable def toMv (t : Tensor n) : MvPolynomial (Fin n) ℚ := arrPoly t.deg t.coeffs

theorem coeff_box (t : Tensor n) (e : Fin n → Fin (t.deg + 1)) :
    t.coeff (fun i => (e i : ℕ)) = t.coeffs.getD (flatIndex (t.deg + 1) fun i => (e i : ℕ)) 0 := by
  have hall : ((List.finRange n).all fun i => decide ((e i : ℕ) ≤ t.deg)) = true := by
    simp only [List.all_eq_true, decide_eq_true_eq]
    intro i _
    exact Nat.lt_succ_iff.1 (e i).isLt
  simp only [coeff, hall, ite_true]

/-- `eval` is the evaluation of the polynomial `toMv`. -/
theorem eval_eq_aeval (t : Tensor n) (x : Fin n → ℝ) :
    t.eval x = MvPolynomial.aeval x (toMv t) := by
  simp only [eval, toMv, arrPoly, map_sum, aeval_mono, coeff_box]

theorem arrPoly_replicate (d N : ℕ) :
    (arrPoly d (Array.replicate N 0) : MvPolynomial (Fin n) ℚ) = 0 := by
  unfold arrPoly
  apply Finset.sum_eq_zero
  intro e _
  have h0 : (Array.replicate N (0 : ℚ)).getD (flatIndex (d + 1) fun i => (e i : ℕ)) 0 = 0 := by
    simp only [Array.getD_eq_getD_getElem?, Array.getElem?_replicate]
    split <;> rfl
  rw [h0, mono_zero]

/-- Adding `c` at the flat index of `e0` adds the monomial `c · s^e0`. -/
theorem arrPoly_set (d : ℕ) (arr : Array ℚ) (hsz : arr.size = (d + 1) ^ n)
    (e0 : Fin n → Fin (d + 1)) (c : ℚ) :
    (arrPoly d (arr.set! (flatIndex (d + 1) fun i => (e0 i : ℕ))
        (arr.getD (flatIndex (d + 1) fun i => (e0 i : ℕ)) 0 + c)) : MvPolynomial (Fin n) ℚ)
      = arrPoly d arr + mono (fun i => (e0 i : ℕ)) c := by
  have hidx : flatIndex (d + 1) (fun i => (e0 i : ℕ)) < arr.size := hsz ▸ flatIndex_lt (d + 1) e0
  have hpt : ∀ e : Fin n → Fin (d + 1),
      mono (fun i => (e i : ℕ))
          ((arr.set! (flatIndex (d + 1) fun i => (e0 i : ℕ))
            (arr.getD (flatIndex (d + 1) fun i => (e0 i : ℕ)) 0 + c)).getD
              (flatIndex (d + 1) fun i => (e i : ℕ)) 0)
        = mono (fun i => (e i : ℕ)) (arr.getD (flatIndex (d + 1) fun i => (e i : ℕ)) 0)
          + (if e = e0 then mono (fun i => (e i : ℕ)) c else 0 : MvPolynomial (Fin n) ℚ) := by
    intro e
    by_cases he : e = e0
    · subst he
      simp [hidx, mono_add]
    · have hne : flatIndex (d + 1) (fun i => (e0 i : ℕ)) ≠ flatIndex (d + 1) fun i => (e i : ℕ) :=
        fun h => he (flatIndex_injective _ _ _ h.symm)
      simp [hne, he]
  unfold arrPoly
  simp only [hpt, Finset.sum_add_distrib, Finset.sum_ite_eq', Finset.mem_univ, ite_true]

/-- Accumulating into a layout: if every step adds the polynomial `sem t`, the fold adds their
sum. -/
theorem foldl_arrPoly {τ : Type} (d : ℕ) (step : Array ℚ → τ → Array ℚ)
    (sem : τ → MvPolynomial (Fin n) ℚ) (l : List τ)
    (h : ∀ t ∈ l, ∀ out : Array ℚ, out.size = (d + 1) ^ n →
      (step out t).size = (d + 1) ^ n ∧ arrPoly d (step out t) = arrPoly d out + sem t) :
    ∀ out : Array ℚ, out.size = (d + 1) ^ n →
      (l.foldl step out).size = (d + 1) ^ n
        ∧ arrPoly d (l.foldl step out) = arrPoly d out + (l.map sem).sum := by
  induction l with
  | nil => intro out hsz; simp [hsz]
  | cons a l ih =>
    intro out hsz
    simp only [List.foldl_cons, List.map_cons, List.sum_cons]
    obtain ⟨h1, h2⟩ := h a (by simp) out hsz
    obtain ⟨h3, h4⟩ := ih (fun t ht => h t (by simp [ht])) _ h1
    exact ⟨h3, by rw [h4, h2, add_assoc]⟩

/-! ### `support` lists the monomials -/

/-- The monomial a listed term `(exponent array, coefficient)` denotes. -/
noncomputable def termMono (p : Array ℕ × ℚ) : MvPolynomial (Fin n) ℚ :=
  mono (fun i : Fin n => p.1.getD i.val 0) p.2

theorem support_eq_foldl (t : Tensor n) :
    t.support = (List.range ((t.deg + 1) ^ n)).foldl
      (fun (out : Array (Array ℕ × ℚ)) idx =>
        if (t.coeffs.getD idx 0 != 0) = true then
          out.push (decode n (t.deg + 1) idx, t.coeffs.getD idx 0)
        else out) #[] := by
  unfold support
  simp only [Std.Legacy.Range.forIn_eq_forIn_range', Std.Legacy.Range.size]
  rw [forIn_list_id _ _ _
    (fun (out : Array (Array ℕ × ℚ)) idx =>
      if (t.coeffs.getD idx 0 != 0) = true then
        out.push (decode n (t.deg + 1) idx, t.coeffs.getD idx 0)
      else out)
    (by intro a b; split <;> rfl)]
  simp [List.range_eq_range']

/-- The terms listed by `support` sum to the polynomial of the tensor. -/
theorem sum_support (t : Tensor n) :
    ((t.support.toList.map termMono).sum : MvPolynomial (Fin n) ℚ) = toMv t := by
  rw [support_eq_foldl]
  have key := foldl_range_induction ((t.deg + 1) ^ n)
    (fun (out : Array (Array ℕ × ℚ)) idx =>
      if (t.coeffs.getD idx 0 != 0) = true then
        out.push (decode n (t.deg + 1) idx, t.coeffs.getD idx 0)
      else out) #[]
    (fun k out => ((out.toList.map termMono).sum : MvPolynomial (Fin n) ℚ)
      = ∑ idx ∈ Finset.range k,
          mono (fun i : Fin n => idx / (t.deg + 1) ^ (n - 1 - i.val) % (t.deg + 1))
            (t.coeffs.getD idx 0))
    (by simp)
    (by
      intro k _ out ih
      rw [Finset.sum_range_succ, ← ih]
      split
      · have hdec : (fun i : Fin n => (decode n (t.deg + 1) k).getD i.val 0)
            = fun i : Fin n => k / (t.deg + 1) ^ (n - 1 - i.val) % (t.deg + 1) := by
          funext i
          exact (decode_spec n (t.deg + 1) k).2 i.val i.isLt
        rw [Array.toList_push, List.map_append, List.sum_append]
        simp only [List.map_cons, List.map_nil, List.sum_cons, List.sum_nil, add_zero, termMono,
          hdec]
      · rename_i hc
        have h0 : t.coeffs.getD k 0 = 0 := by simpa using hc
        rw [h0, mono_zero, add_zero])
  rw [key, toMv, arrPoly, sum_range_eq_sum_box]
  apply Finset.sum_congr rfl
  intro e _
  congr 1
  funext i
  exact flatIndex_digit _ e i

/-! ### `ofTerms` sums the listed monomials that fit -/

theorem ofTerms_eq_foldl (deg : ℕ) (terms : Array (Array ℕ × ℚ)) :
    (ofTerms deg terms : Tensor n) = ⟨deg, terms.foldl
      (fun (out : Array ℚ) p =>
        if ((Array.range n).all fun i => decide (p.1.getD i 0 ≤ deg)) = true then
          out.set! (encode n (deg + 1) p.1) (out.getD (encode n (deg + 1) p.1) 0 + p.2)
        else out)
      (Array.replicate ((deg + 1) ^ n) 0)⟩ := by
  unfold ofTerms
  simp only []
  rw [forIn_array_id _ _ _
    (fun (out : Array ℚ) p =>
      if ((Array.range n).all fun i => decide (p.1.getD i 0 ≤ deg)) = true then
        out.set! (encode n (deg + 1) p.1) (out.getD (encode n (deg + 1) p.1) 0 + p.2)
      else out)
    (by rintro ⟨e, c⟩ b; simp only []; split <;> rfl)]
  rfl

theorem ofTerms_deg (deg : ℕ) (terms : Array (Array ℕ × ℚ)) :
    (ofTerms deg terms : Tensor n).deg = deg := by
  rw [ofTerms_eq_foldl]

theorem all_range_iff (deg : ℕ) (e : Array ℕ) :
    ((Array.range n).all fun i => decide (e.getD i 0 ≤ deg)) = true
      ↔ ∀ i, i < n → e.getD i 0 ≤ deg := by
  rw [Array.all_eq_true_iff_forall_mem]
  simp only [Array.mem_range, decide_eq_true_eq]

/-- One accumulation step of `ofTerms` / `mul`: adding `c` at the flat index of an exponent
array that fits the layout adds its monomial. -/
theorem arrPoly_accum (d : ℕ) (out : Array ℚ) (hsz : out.size = (d + 1) ^ n) (f : Fin n → ℕ)
    (hfit : ∀ i, f i ≤ d) (c : ℚ) :
    (out.set! (flatIndex (d + 1) f) (out.getD (flatIndex (d + 1) f) 0 + c)).size = (d + 1) ^ n
      ∧ (arrPoly d (out.set! (flatIndex (d + 1) f) (out.getD (flatIndex (d + 1) f) 0 + c))
          : MvPolynomial (Fin n) ℚ) = arrPoly d out + mono f c := by
  refine ⟨by simp [hsz], ?_⟩
  exact arrPoly_set d out hsz (fun i => ⟨f i, Nat.lt_succ_of_le (hfit i)⟩) c

/-- `ofTerms` denotes the sum of the listed monomials that fit its layout. -/
theorem toMv_ofTerms (deg : ℕ) (terms : Array (Array ℕ × ℚ)) :
    toMv (ofTerms deg terms : Tensor n)
      = (terms.toList.map fun p =>
          if ∀ i, i < n → p.1.getD i 0 ≤ deg then termMono p else 0).sum := by
  rw [ofTerms_eq_foldl]
  change arrPoly deg _ = _
  rw [← Array.foldl_toList]
  have key := foldl_arrPoly (n := n) deg
    (fun (out : Array ℚ) (p : Array ℕ × ℚ) =>
      if ((Array.range n).all fun i => decide (p.1.getD i 0 ≤ deg)) = true then
        out.set! (encode n (deg + 1) p.1) (out.getD (encode n (deg + 1) p.1) 0 + p.2)
      else out)
    (fun p => if ∀ i, i < n → p.1.getD i 0 ≤ deg then termMono p else 0)
    terms.toList
    (by
      intro p _ out hsz
      by_cases hfit : ∀ i, i < n → p.1.getD i 0 ≤ deg
      · rw [ite_eq_left ((all_range_iff deg p.1).2 hfit), ite_eq_left hfit, encode_eq_flatIndex]
        exact arrPoly_accum deg out hsz _ (fun i => hfit i.val i.isLt) p.2
      · have hno : ¬ (((Array.range n).all fun i => decide (p.1.getD i 0 ≤ deg)) = true) :=
          fun h => hfit ((all_range_iff deg p.1).1 h)
        rw [ite_eq_right hno, ite_eq_right hfit, add_zero]
        exact ⟨hsz, rfl⟩)
    (Array.replicate ((deg + 1) ^ n) 0) (by simp)
  rw [key.2, arrPoly_replicate, zero_add]

/-- If every listed term fits, `ofTerms` denotes the sum of the listed monomials. -/
theorem toMv_ofTerms_of_fit (deg : ℕ) (terms : Array (Array ℕ × ℚ))
    (hfit : ∀ p ∈ terms, ∀ i, i < n → p.1.getD i 0 ≤ deg) :
    toMv (ofTerms deg terms : Tensor n) = (terms.toList.map termMono).sum := by
  rw [toMv_ofTerms]
  congr 1
  apply List.map_congr_left
  intro p hp
  rw [ite_eq_left (hfit p (Array.mem_toList_iff.1 hp))]

/-! ### `varDegsOf` and `maxDeg` bound the listed exponents -/

theorem le_foldl_max (l : List ℕ) (init : ℕ) :
    init ≤ l.foldl max init ∧ ∀ x ∈ l, x ≤ l.foldl max init := by
  induction l generalizing init with
  | nil => simp
  | cons a l ih =>
    simp only [List.foldl_cons]
    obtain ⟨h1, h2⟩ := ih (max init a)
    refine ⟨le_trans (le_max_left _ _) h1, ?_⟩
    intro x hx
    rcases List.mem_cons.1 hx with rfl | hx
    · exact le_trans (le_max_right _ _) h1
    · exact h2 x hx

theorem le_maxDeg (ds : Array ℕ) (x : ℕ) (hx : x ∈ ds) : x ≤ maxDeg ds := by
  unfold maxDeg
  rw [← Array.foldl_toList]
  exact (le_foldl_max _ _).2 x (Array.mem_toList_iff.2 hx)

theorem getD_le_maxDeg (ds : Array ℕ) (i : ℕ) : ds.getD i 0 ≤ maxDeg ds := by
  by_cases h : i < ds.size
  · have hget : ds.getD i 0 = ds[i] := by simp [h]
    rw [hget]
    exact le_maxDeg _ _ (Array.getElem_mem h)
  · have hget : ds.getD i 0 = 0 := by simp [h]
    rw [hget]
    exact Nat.zero_le _

/-- One step of the inner loop of `varDegsOf`. -/
def raise (e out : Array ℕ) (i : ℕ) : Array ℕ :=
  if e.getD i 0 > out.getD i 0 then out.set! i (e.getD i 0) else out

theorem varDegsOf_eq_foldl (n : ℕ) (terms : Array (Array ℕ × ℚ)) :
    varDegsOf n terms
      = terms.foldl (fun (out : Array ℕ) p => (List.range n).foldl (raise p.1) out)
          (Array.replicate n 0) := by
  unfold varDegsOf
  simp only [Std.Legacy.Range.forIn_eq_forIn_range', Std.Legacy.Range.size]
  rw [forIn_array_id _ _ _
    (fun (out : Array ℕ) (p : Array ℕ × ℚ) => (List.range n).foldl (raise p.1) out)
    (by
      rintro ⟨e, c⟩ b
      simp only []
      rw [forIn_list_id _ _ _ (raise e) (by intro a b; unfold raise; split <;> rfl)]
      simp [List.range_eq_range'])]
  rfl

theorem raise_spec (e out : Array ℕ) (i : ℕ) :
    (raise e out i).size = out.size ∧ (∀ j, out.getD j 0 ≤ (raise e out i).getD j 0)
      ∧ (i < out.size → e.getD i 0 ≤ (raise e out i).getD i 0) := by
  unfold raise
  split
  · rename_i h
    refine ⟨by simp, ?_, ?_⟩
    · intro j
      by_cases hj : i = j
      · subst hj
        by_cases hi : i < out.size
        · simp only [Array.getD_eq_getD_getElem?, Array.set!_eq_setIfInBounds,
            Array.getElem?_setIfInBounds, ite_true, hi, Option.getD_some] at h ⊢
          exact le_of_lt h
        · simp [hi]
      · simp [hj]
    · intro hi
      simp [hi]
  · rename_i h
    exact ⟨rfl, fun _ => le_refl _, fun _ => not_lt.1 h⟩

theorem raiseAll_spec (n : ℕ) (e out : Array ℕ) (hsz : out.size = n) :
    ((List.range n).foldl (raise e) out).size = n
      ∧ (∀ j, out.getD j 0 ≤ ((List.range n).foldl (raise e) out).getD j 0)
      ∧ (∀ i, i < n → e.getD i 0 ≤ ((List.range n).foldl (raise e) out).getD i 0) := by
  have key := foldl_range_induction n (raise e) out
    (fun k b => b.size = n ∧ (∀ j, out.getD j 0 ≤ b.getD j 0)
      ∧ (∀ i, i < k → e.getD i 0 ≤ b.getD i 0))
    ⟨hsz, fun _ => le_refl _, fun i hi => absurd hi (Nat.not_lt_zero i)⟩
    (by
      rintro k hk b ⟨hb, hmono, hle⟩
      obtain ⟨h1, h2, h3⟩ := raise_spec e b k
      refine ⟨h1.trans hb, fun j => le_trans (hmono j) (h2 j), ?_⟩
      intro i hi
      rcases Nat.lt_succ_iff_lt_or_eq.1 hi with hlt | rfl
      · exact le_trans (hle i hlt) (h2 i)
      · exact h3 (hb ▸ hk))
  exact key

/-- Per variable, `varDegsOf` bounds the exponent of every listed term. -/
theorem varDegsOf_spec (n : ℕ) (terms : Array (Array ℕ × ℚ)) :
    ∀ p ∈ terms, ∀ i, i < n → p.1.getD i 0 ≤ (varDegsOf n terms).getD i 0 := by
  rw [varDegsOf_eq_foldl, ← Array.foldl_toList]
  have key : ∀ (l : List (Array ℕ × ℚ)) (out : Array ℕ), out.size = n →
      (l.foldl (fun (out : Array ℕ) p => (List.range n).foldl (raise p.1) out) out).size = n
      ∧ (∀ j, out.getD j 0 ≤
          (l.foldl (fun (out : Array ℕ) p => (List.range n).foldl (raise p.1) out) out).getD j 0)
      ∧ (∀ p ∈ l, ∀ i, i < n → p.1.getD i 0 ≤
          (l.foldl (fun (out : Array ℕ) p => (List.range n).foldl (raise p.1) out)
            out).getD i 0) := by
    intro l
    induction l with
    | nil => intro out hsz; exact ⟨hsz, fun _ => le_refl _, fun p hp => absurd hp (by simp)⟩
    | cons a l ih =>
      intro out hsz
      simp only [List.foldl_cons]
      obtain ⟨h1, h2, h3⟩ := raiseAll_spec n a.1 out hsz
      obtain ⟨g1, g2, g3⟩ := ih _ h1
      refine ⟨g1, fun j => le_trans (h2 j) (g2 j), ?_⟩
      intro p hp i hi
      rcases List.mem_cons.1 hp with rfl | hp
      · exact le_trans (h3 i hi) (g2 i)
      · exact g3 p hp i hi
  intro p hp
  exact (key terms.toList (Array.replicate n 0) (by simp)).2.2 p (Array.mem_toList_iff.2 hp)

/-- Every listed term fits the layout of degree `maxDeg (varDegsOf n terms)`. -/
theorem fit_maxDeg (terms : Array (Array ℕ × ℚ)) :
    ∀ p ∈ terms, ∀ i, i < n → p.1.getD i 0 ≤ maxDeg (varDegsOf n terms) :=
  fun p hp i hi => le_trans (varDegsOf_spec n terms p hp i hi) (getD_le_maxDeg _ _)

/-! ### The operations, on `toMv` -/

theorem toMv_trim (t : Tensor n) : toMv t.trim = toMv t := by
  unfold trim
  simp only []
  rw [toMv_ofTerms_of_fit _ _ (fit_maxDeg _), sum_support]

theorem toMv_padTo (t q : Tensor n) (d : ℕ) (h : t.padTo? d = some q) : toMv q = toMv t := by
  unfold padTo? at h
  simp only [] at h
  split_ifs at h with hd
  obtain rfl := Option.some.inj h
  rw [toMv_ofTerms_of_fit _ _ (fun p hp i hi => le_trans (fit_maxDeg _ p hp i hi) hd), sum_support]

theorem padTo_deg (t q : Tensor n) (d : ℕ) (h : t.padTo? d = some q) : q.deg = d := by
  unfold padTo? at h
  simp only [] at h
  split_ifs at h with hd
  obtain rfl := Option.some.inj h
  exact ofTerms_deg _ _

theorem toMv_add (a b : Tensor n) : toMv (a.add b) = toMv a + toMv b := by
  unfold add
  simp only []
  rw [toMv_trim, toMv_ofTerms_of_fit _ _ (fit_maxDeg _), Array.toList_append, List.map_append,
    List.sum_append, sum_support, sum_support]

theorem toMv_zero : toMv (zero : Tensor n) = 0 := by
  have h := arrPoly_replicate (n := n) 0 1
  simpa [toMv, zero] using h

theorem toMv_const (c : ℚ) : toMv (const c : Tensor n) = MvPolynomial.C c := by
  change arrPoly 0 #[c] = _
  unfold arrPoly
  have hall : ∀ e : Fin n → Fin (0 + 1), e = fun _ => 0 := fun e =>
    funext fun i => Fin.ext (by have := (e i).isLt; simp only [Fin.val_zero]; omega)
  rw [Fintype.sum_eq_single (fun _ => 0) (fun e he => absurd (hall e) he)]
  have h0 : flatIndex (0 + 1) (fun _ : Fin n => (0 : ℕ)) = 0 := by simp [flatIndex_eq_sum]
  have hz : (Finsupp.equivFunOnFinite.symm (fun _ : Fin n => (0 : ℕ))) = 0 := by
    ext i
    simp
  simp only [Fin.val_zero, h0, mono, hz]
  simp

theorem toMv_scale (a : Tensor n) (c : ℚ) : toMv (a.scale c) = MvPolynomial.C c * toMv a := by
  unfold scale
  split
  · rename_i hc
    have h0 : c = 0 := by simpa using hc
    subst h0
    simp [toMv_zero]
  · simp only []
    rw [toMv_ofTerms_of_fit _ _ (fit_maxDeg _), ← sum_support a, Array.toList_map, List.map_map,
      ← List.sum_map_mul_left]
    congr 1
    apply List.map_congr_left
    rintro ⟨e, v⟩ _
    simp [termMono, mono, MvPolynomial.C_mul_monomial]

/-- The accumulation loop of `mul`, as a fold over the two lists of terms. -/
def mulAcc (n base : ℕ) (sa sb : List (Array ℕ × ℚ)) (out : Array ℚ) : Array ℚ :=
  sa.foldl (fun (out : Array ℚ) p =>
    sb.foldl (fun (out : Array ℚ) q =>
      out.set! (encode n base p.1 + encode n base q.1)
        (out.getD (encode n base p.1 + encode n base q.1) 0 + p.2 * q.2)) out) out

theorem mul_eq (a b : Tensor n) :
    a.mul b = if (a.support.isEmpty || b.support.isEmpty) = true then zero else
      (⟨maxDeg ((Array.range n).map fun i =>
          (varDegsOf n a.support).getD i 0 + (varDegsOf n b.support).getD i 0),
        mulAcc n (maxDeg ((Array.range n).map fun i =>
          (varDegsOf n a.support).getD i 0 + (varDegsOf n b.support).getD i 0) + 1)
          a.support.toList b.support.toList
          (Array.replicate ((maxDeg ((Array.range n).map fun i =>
            (varDegsOf n a.support).getD i 0 + (varDegsOf n b.support).getD i 0) + 1) ^ n) 0)⟩
        : Tensor n).trim := by
  unfold mul
  simp only []
  split
  · rfl
  · rw [forIn_array_id _ _ _
      (fun (out : Array ℚ) (x : ℕ × ℚ) =>
        (b.support.map fun (q : Array ℕ × ℚ) =>
            (encode n (maxDeg ((Array.range n).map fun i =>
              (varDegsOf n a.support).getD i 0 + (varDegsOf n b.support).getD i 0) + 1) q.1,
              q.2)).foldl
          (fun (out : Array ℚ) (y : ℕ × ℚ) =>
            out.set! (x.1 + y.1) (out.getD (x.1 + y.1) 0 + x.2 * y.2)) out)
      (by
        rintro ⟨i, ca⟩ out
        simp only []
        rw [forIn_array_id _ _ _
          (fun (out : Array ℚ) (y : ℕ × ℚ) =>
            out.set! (i + y.1) (out.getD (i + y.1) 0 + ca * y.2))
          (by rintro ⟨j, cb⟩ out; rfl)]
        rfl)]
    simp only [mulAcc, ← Array.foldl_toList, Array.toList_map, List.foldl_map, pure_bind,
      Id.run_pure]

/-- The accumulation loop of `mul` adds the product of the two sums of monomials. -/
theorem arrPoly_mulAcc (d : ℕ) (sa sb : List (Array ℕ × ℚ))
    (hfit : ∀ p ∈ sa, ∀ q ∈ sb, ∀ i, i < n → p.1.getD i 0 + q.1.getD i 0 ≤ d)
    (out : Array ℚ) (hsz : out.size = (d + 1) ^ n) :
    (arrPoly d (mulAcc n (d + 1) sa sb out) : MvPolynomial (Fin n) ℚ)
      = arrPoly d out + (sa.map termMono).sum * (sb.map termMono).sum := by
  have inner : ∀ p ∈ sa, ∀ out : Array ℚ, out.size = (d + 1) ^ n →
      (sb.foldl (fun (out : Array ℚ) q =>
        out.set! (encode n (d + 1) p.1 + encode n (d + 1) q.1)
          (out.getD (encode n (d + 1) p.1 + encode n (d + 1) q.1) 0 + p.2 * q.2)) out).size
        = (d + 1) ^ n
      ∧ (arrPoly d (sb.foldl (fun (out : Array ℚ) q =>
        out.set! (encode n (d + 1) p.1 + encode n (d + 1) q.1)
          (out.getD (encode n (d + 1) p.1 + encode n (d + 1) q.1) 0 + p.2 * q.2)) out)
          : MvPolynomial (Fin n) ℚ)
        = arrPoly d out + termMono p * (sb.map termMono).sum := by
    intro p hp out hsz
    have key := foldl_arrPoly (n := n) d
      (fun (out : Array ℚ) (q : Array ℕ × ℚ) =>
        out.set! (encode n (d + 1) p.1 + encode n (d + 1) q.1)
          (out.getD (encode n (d + 1) p.1 + encode n (d + 1) q.1) 0 + p.2 * q.2))
      (fun q => termMono p * termMono q) sb
      (by
        intro q hq out hsz
        have hidx : encode n (d + 1) p.1 + encode n (d + 1) q.1
            = flatIndex (d + 1) (fun i : Fin n => p.1.getD i.val 0 + q.1.getD i.val 0) := by
          rw [encode_eq_flatIndex, encode_eq_flatIndex, ← flatIndex_add]
        simp only [hidx, termMono, mono_mul]
        exact arrPoly_accum d out hsz _ (fun i => hfit p hp q hq i.val i.isLt) (p.2 * q.2))
      out hsz
    rw [List.sum_map_mul_left] at key
    exact key
  have key := foldl_arrPoly (n := n) d
    (fun (out : Array ℚ) (p : Array ℕ × ℚ) =>
      sb.foldl (fun (out : Array ℚ) q =>
        out.set! (encode n (d + 1) p.1 + encode n (d + 1) q.1)
          (out.getD (encode n (d + 1) p.1 + encode n (d + 1) q.1) 0 + p.2 * q.2)) out)
    (fun p => termMono p * (sb.map termMono).sum) sa inner out hsz
  rw [List.sum_map_mul_right] at key
  exact key.2

theorem toMv_mul (a b : Tensor n) : toMv (a.mul b) = toMv a * toMv b := by
  rw [mul_eq]
  split
  · rename_i hemp
    rw [toMv_zero, ← sum_support a, ← sum_support b]
    rw [Bool.or_eq_true] at hemp
    rcases hemp with h | h
    · have : a.support.toList = [] := by simpa using h
      simp [this]
    · have : b.support.toList = [] := by simpa using h
      simp [this]
  · rw [toMv_trim]
    change arrPoly _ _ = _
    rw [arrPoly_mulAcc _ _ _ _ _ (by simp), arrPoly_replicate, zero_add, sum_support, sum_support]
    intro p hp q hq i hi
    have h1 := varDegsOf_spec n a.support p (Array.mem_toList_iff.1 hp) i hi
    have h2 := varDegsOf_spec n b.support q (Array.mem_toList_iff.1 hq) i hi
    refine le_trans (Nat.add_le_add h1 h2) (le_maxDeg _ _ ?_)
    exact Array.mem_map.2 ⟨i, Array.mem_range.2 hi, rfl⟩

/-! ### The lemmas T1–T7 -/

theorem foldl_mul_eq_prod {α : Type} (l : List α) (g : α → ℚ) (c : ℚ) :
    l.foldl (fun term i => term * g i) c = c * (l.map g).prod := by
  induction l generalizing c with
  | nil => simp
  | cons a l ih => simp [ih, mul_assoc]

theorem foldl_add_eq_sum {α : Type} (l : List α) (g : α → ℚ) (c : ℚ) :
    l.foldl (fun acc p => acc + g p) c = c + (l.map g).sum := by
  induction l generalizing c with
  | nil => simp
  | cons a l ih => simp [ih, add_assoc]

/-- [T1] The computable rational evaluation agrees with the reference semantics. -/
theorem evalQ_cast (t : Tensor n) (x : Fin n → ℚ) :
    ((t.evalQ x : ℚ) : ℝ) = t.eval (fun i => (x i : ℝ)) := by
  have hq : t.evalQ x
      = (t.support.toList.map fun p => p.2 * ∏ i : Fin n, x i ^ p.1.getD i.val 0).sum := by
    unfold evalQ
    rw [← Array.foldl_toList]
    have hstep : (fun (acc : ℚ) (p : Array ℕ × ℚ) =>
        match p with
        | (e, c) => acc + (List.finRange n).foldl (fun term i => term * x i ^ e.getD i.val 0) c)
        = fun acc p => acc + p.2 * ∏ i : Fin n, x i ^ p.1.getD i.val 0 := by
      funext acc ⟨e, c⟩
      simp only []
      rw [foldl_mul_eq_prod, ← List.ofFn_eq_map, List.prod_ofFn]
    rw [hstep, foldl_add_eq_sum, zero_add]
  rw [eval_eq_aeval, ← sum_support, map_list_sum, List.map_map, hq, Rat.cast_list_sum,
    List.map_map]
  congr 1
  apply List.map_congr_left
  rintro ⟨e, c⟩ _
  simp [termMono, aeval_mono]

/-- [T2] The constant tensor denotes the constant function. -/
theorem eval_const (c : ℚ) (x : Fin n → ℝ) : (Tensor.const c : Tensor n).eval x = (c : ℝ) := by
  rw [eval_eq_aeval, toMv_const]
  simp

/-- [T3] `add` denotes the pointwise sum. -/
theorem eval_add (a b : Tensor n) (x : Fin n → ℝ) : (a + b).eval x = a.eval x + b.eval x := by
  change (a.add b).eval x = _
  rw [eval_eq_aeval, toMv_add, map_add, ← eval_eq_aeval, ← eval_eq_aeval]

/-- [T4] `scale` denotes the multiplication by a constant. -/
theorem eval_scale (a : Tensor n) (c : ℚ) (x : Fin n → ℝ) :
    (a.scale c).eval x = (c : ℝ) * a.eval x := by
  rw [eval_eq_aeval, toMv_scale, map_mul, ← eval_eq_aeval]
  simp

/-- [T5] `mul` denotes the pointwise product. -/
theorem eval_mul (a b : Tensor n) (x : Fin n → ℝ) : (a * b).eval x = a.eval x * b.eval x := by
  change (a.mul b).eval x = _
  rw [eval_eq_aeval, toMv_mul, map_mul, ← eval_eq_aeval, ← eval_eq_aeval]

/-- [T6] Degree padding does not change the polynomial. -/
theorem eval_padTo (t q : Tensor n) (d : ℕ) (h : t.padTo? d = some q) (x : Fin n → ℝ) :
    q.eval x = t.eval x := by
  rw [eval_eq_aeval, toMv_padTo t q d h, ← eval_eq_aeval]

/-- [T7] `beqPoly` is sound: tensors it identifies denote the same function. -/
theorem eval_eq_of_beqPoly (a b : Tensor n) (h : a.beqPoly b = true) (x : Fin n → ℝ) :
    a.eval x = b.eval x := by
  unfold beqPoly at h
  simp only [Bool.and_eq_true, beq_iff_eq] at h
  have htrim : a.trim = b.trim := by
    cases ha : a.trim
    cases hb : b.trim
    rw [ha, hb] at h
    simp only at h
    rw [h.1, h.2]
  rw [eval_eq_aeval, eval_eq_aeval, ← toMv_trim a, ← toMv_trim b, htrim]

end Tensor

end CnpVerify
