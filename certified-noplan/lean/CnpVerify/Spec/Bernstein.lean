/-
CnpVerify.Spec.Bernstein — what the Bernstein test proves (L2: B0 and B1 proved).

If every Bernstein coefficient of `p` over the box `b` is non-negative, then `p ≥ 0` on `b`.

Method (L2). A coefficient array is read against per-axis weights `g i k` (`arrSum`): with
`g i k = xᵢ^k` it is the value of the polynomial at `x`; with `g i k = B_{k,d}(tᵢ)` it is the
value of a Bernstein form at `t`. Applying a matrix along one axis (`applyAxis`) moves the matrix
onto the weights of that axis (`arrSum_applyAxis`). The matrix of the checker is `B · S` with `S`
the affine substitution `s = lo + (hi - lo) t` (binomial theorem) and `B` the
monomial-to-Bernstein change of basis on `[0,1]`, whose correctness is the identity
`t^k = Σ_j C(j,k)/C(d,k) · B_{j,d}(t)` (`bern_inverse`).
-/
import Mathlib
import CnpVerify.Bernstein
import CnpVerify.Spec.Tensor

namespace CnpVerify

variable {n : ℕ}

/-- The box as a subset of `ℝⁿ`: `{x | ∀ i, loᵢ ≤ xᵢ ≤ hiᵢ}`. -/
def Box.toSet (b : Box n) : Set (Fin n → ℝ) :=
  {x | ∀ i : Fin n, (b.lo i : ℝ) ≤ x i ∧ x i ≤ (b.hi i : ℝ)}

/-- [B0] The computable binomial coefficient is `Nat.choose`. -/
theorem binom_eq_choose (m k : ℕ) : binom m k = m.choose k := by
  induction k with
  | zero => simp [binom]
  | succ k ih =>
    rw [binom, ih]
    exact Nat.div_eq_of_eq_mul_left (Nat.succ_pos k) (Nat.choose_succ_right_eq m k).symm

/-! ### A coefficient array read against per-axis weights -/

/-- Weight of the flat index `j`: the product over the axes of the weight of its digit. -/
noncomputable def wt (d : ℕ) (g : Fin n → ℕ → ℝ) (j : ℕ) : ℝ :=
  ∏ i : Fin n, g i (j / (d + 1) ^ (n - 1 - i.val) % (d + 1))

/-- `Σ_e arr[e] · ∏ᵢ g i (eᵢ)` over the layout of degree `d`. -/
noncomputable def arrSum (d : ℕ) (g : Fin n → ℕ → ℝ) (arr : Array ℚ) : ℝ :=
  ∑ j ∈ Finset.range ((d + 1) ^ n), (arr.getD j 0 : ℝ) * wt d g j

theorem wt_flatIndex (d : ℕ) (g : Fin n → ℕ → ℝ) (e : Fin n → Fin (d + 1)) :
    wt d g (Tensor.flatIndex (d + 1) fun i => (e i : ℕ)) = ∏ i, g i (e i) := by
  unfold wt
  apply Finset.prod_congr rfl
  intro i _
  rw [Tensor.flatIndex_digit]

theorem arrSum_eq_box (d : ℕ) (g : Fin n → ℕ → ℝ) (arr : Array ℚ) :
    arrSum d g arr = ∑ e : Fin n → Fin (d + 1),
      (arr.getD (Tensor.flatIndex (d + 1) fun i => (e i : ℕ)) 0 : ℝ) * ∏ i, g i (e i) := by
  unfold arrSum
  rw [Tensor.sum_range_eq_sum_box]
  simp only [wt_flatIndex]

/-- With the weights `xᵢ^k`, `arrSum` is the value of the polynomial. -/
theorem eval_eq_arrSum (t : Tensor n) (x : Fin n → ℝ) :
    t.eval x = arrSum t.deg (fun i k => x i ^ k) t.coeffs := by
  rw [arrSum_eq_box]
  simp only [Tensor.eval, Tensor.coeff_box]

/-- `arrSum` only reads the weights of the digits `≤ d`. -/
theorem arrSum_congr (d : ℕ) (g g' : Fin n → ℕ → ℝ) (arr : Array ℚ)
    (h : ∀ i k, k ≤ d → g i k = g' i k) : arrSum d g arr = arrSum d g' arr := by
  unfold arrSum wt
  apply Finset.sum_congr rfl
  intro j _
  congr 1
  apply Finset.prod_congr rfl
  intro i _
  exact h i _ (Nat.lt_succ_iff.1 (Nat.mod_lt _ (Nat.succ_pos d)))

/-- `arrSum` only reads the entries inside the layout. -/
theorem arrSum_getD_congr (d : ℕ) (g : Fin n → ℕ → ℝ) (a b : Array ℚ)
    (h : ∀ j, j < (d + 1) ^ n → a.getD j 0 = b.getD j 0) : arrSum d g a = arrSum d g b := by
  unfold arrSum
  apply Finset.sum_congr rfl
  intro j hj
  rw [h j (Finset.mem_range.1 hj)]

theorem arrSum_replicate (d N : ℕ) (g : Fin n → ℕ → ℝ) :
    arrSum d g (Array.replicate N 0) = 0 := by
  unfold arrSum
  apply Finset.sum_eq_zero
  intro j _
  have h0 : (Array.replicate N (0 : ℚ)).getD j 0 = 0 := by
    simp only [Array.getD_eq_getD_getElem?, Array.getElem?_replicate]
    split <;> rfl
  rw [h0]
  simp

/-- Adding `v` at the flat index `j` adds `v · wt j`. -/
theorem arrSum_set (d : ℕ) (g : Fin n → ℕ → ℝ) (arr : Array ℚ) (hsz : arr.size = (d + 1) ^ n)
    (j : ℕ) (hj : j < (d + 1) ^ n) (v : ℚ) :
    arrSum d g (arr.set! j (arr.getD j 0 + v)) = arrSum d g arr + (v : ℝ) * wt d g j := by
  have hjs : j < arr.size := hsz ▸ hj
  have hpt : ∀ k, ((arr.set! j (arr.getD j 0 + v)).getD k 0 : ℝ) * wt d g k
      = (arr.getD k 0 : ℝ) * wt d g k + (if k = j then (v : ℝ) * wt d g k else 0) := by
    intro k
    by_cases hk : k = j
    · subst hk
      simp [hjs, add_mul]
    · have hne : j ≠ k := fun h => hk h.symm
      simp [hne, hk]
  unfold arrSum
  simp only [hpt, Finset.sum_add_distrib, Finset.sum_ite_eq', Finset.mem_range, hj, ite_true]

/-- Accumulating into a layout: if every step adds `sem t`, the fold adds their sum. -/
theorem foldl_arrSum {τ : Type} (d : ℕ) (g : Fin n → ℕ → ℝ) (step : Array ℚ → τ → Array ℚ)
    (sem : τ → ℝ) (l : List τ)
    (h : ∀ t ∈ l, ∀ out : Array ℚ, out.size = (d + 1) ^ n →
      (step out t).size = (d + 1) ^ n ∧ arrSum d g (step out t) = arrSum d g out + sem t) :
    ∀ out : Array ℚ, out.size = (d + 1) ^ n →
      (l.foldl step out).size = (d + 1) ^ n
        ∧ arrSum d g (l.foldl step out) = arrSum d g out + (l.map sem).sum := by
  induction l with
  | nil => intro out hsz; simp [hsz]
  | cons a l ih =>
    intro out hsz
    simp only [List.foldl_cons, List.map_cons, List.sum_cons]
    obtain ⟨h1, h2⟩ := h a (by simp) out hsz
    obtain ⟨h3, h4⟩ := ih (fun t ht => h t (by simp [ht])) _ h1
    exact ⟨h3, by rw [h4, h2, add_assoc]⟩

theorem list_sum_range (N : ℕ) (f : ℕ → ℝ) :
    ((List.range N).map f).sum = ∑ k ∈ Finset.range N, f k := by
  induction N with
  | zero => simp
  | succ N ih =>
    rw [List.range_succ, List.map_append, List.sum_append, ih, Finset.sum_range_succ]
    simp

/-! ### `applyAxis` moves the matrix onto the weights of its axis -/

/-- Inner loop of `applyAxis`: one row `q` of the matrix. -/
def axisInner (M : RatMatrix) (stride p idx0 : ℕ) (cv : ℚ) (out : Array ℚ) (q : ℕ) : Array ℚ :=
  if ((M.getD q #[]).getD p 0 != 0) = true then
    out.set! (idx0 + q * stride) (out.getD (idx0 + q * stride) 0 + (M.getD q #[]).getD p 0 * cv)
  else out

/-- Outer loop of `applyAxis`: one source entry `idx`. -/
def axisOuter (n d : ℕ) (c : Array ℚ) (ax : ℕ) (M : RatMatrix) (out : Array ℚ) (idx : ℕ) :
    Array ℚ :=
  if (c.getD idx 0 != 0) = true then
    (List.range (d + 1)).foldl
      (axisInner M ((d + 1) ^ (n - 1 - ax)) (idx / (d + 1) ^ (n - 1 - ax) % (d + 1))
        (idx - idx / (d + 1) ^ (n - 1 - ax) % (d + 1) * (d + 1) ^ (n - 1 - ax)) (c.getD idx 0))
      out
  else out

theorem applyAxis_eq_foldl (n d : ℕ) (c : Array ℚ) (ax : ℕ) (M : RatMatrix) :
    applyAxis n d c ax M
      = (List.range ((d + 1) ^ n)).foldl (axisOuter n d c ax M)
          (Array.replicate ((d + 1) ^ n) 0) := by
  unfold applyAxis
  simp only [Std.Legacy.Range.forIn_eq_forIn_range', Std.Legacy.Range.size]
  rw [forIn_list_id _ _ _ (axisOuter n d c ax M) (by
    intro idx out
    unfold axisOuter
    split
    · rw [forIn_list_id _ _ _
        (axisInner M ((d + 1) ^ (n - 1 - ax)) (idx / (d + 1) ^ (n - 1 - ax) % (d + 1))
          (idx - idx / (d + 1) ^ (n - 1 - ax) % (d + 1) * (d + 1) ^ (n - 1 - ax)) (c.getD idx 0))
        (by intro q out; unfold axisInner; split <;> rfl)]
      simp [List.range_eq_range']
    · rfl)]
  simp [List.range_eq_range']

/-- Replacing the digit along `ax` moves the flat index by a multiple of the stride. -/
theorem flatIndex_update (base : ℕ) (e : Fin n → Fin base) (ax : Fin n) (q : Fin base) :
    Tensor.flatIndex base (fun i => (e i : ℕ)) - (e ax : ℕ) * base ^ (n - 1 - ax.val)
        + q.val * base ^ (n - 1 - ax.val)
      = Tensor.flatIndex base (fun i => ((Function.update e ax q) i : ℕ)) := by
  rw [Tensor.flatIndex_eq_sum, Tensor.flatIndex_eq_sum,
    ← Finset.add_sum_erase _ _ (Finset.mem_univ ax),
    ← Finset.add_sum_erase (Finset.univ) (fun i => ((Function.update e ax q) i : ℕ)
      * base ^ (n - 1 - i.val)) (Finset.mem_univ ax)]
  have hrest : ∑ i ∈ Finset.univ.erase ax,
        ((Function.update e ax q) i : ℕ) * base ^ (n - 1 - i.val)
      = ∑ i ∈ Finset.univ.erase ax, (e i : ℕ) * base ^ (n - 1 - i.val) := by
    apply Finset.sum_congr rfl
    intro i hi
    rw [Function.update_of_ne (Finset.ne_of_mem_erase hi)]
  rw [hrest, Function.update_self, Nat.add_sub_cancel_left, add_comm]

/-- Weight of the flat index obtained by replacing the digit along `ax` by `q`. -/
theorem wt_update (d : ℕ) (g : Fin n → ℕ → ℝ) (e : Fin n → Fin (d + 1)) (ax : Fin n) (q : ℕ)
    (hq : q < d + 1) :
    wt d g (Tensor.flatIndex (d + 1) (fun i => (e i : ℕ))
        - (e ax : ℕ) * (d + 1) ^ (n - 1 - ax.val) + q * (d + 1) ^ (n - 1 - ax.val))
      = g ax q * ∏ i ∈ Finset.univ.erase ax, g i (e i) := by
  have h := flatIndex_update (d + 1) e ax ⟨q, hq⟩
  simp only at h
  rw [h, wt_flatIndex, ← Finset.mul_prod_erase _ _ (Finset.mem_univ ax), Function.update_self]
  congr 1
  apply Finset.prod_congr rfl
  intro i hi
  rw [Function.update_of_ne (Finset.ne_of_mem_erase hi)]

/-- Applying `M` along the axis `ax` and reading against the weights `g` is reading the source
against the weights `g` with `g ax` replaced by `p ↦ Σ_q M[q][p] · g ax q`. -/
theorem arrSum_applyAxis (d : ℕ) (g : Fin n → ℕ → ℝ) (c : Array ℚ) (ax : Fin n) (M : RatMatrix) :
    arrSum d g (applyAxis n d c ax.val M)
      = arrSum d (Function.update g ax fun p =>
          ∑ q ∈ Finset.range (d + 1), ((M.getD q #[]).getD p 0 : ℝ) * g ax q) c := by
  rw [applyAxis_eq_foldl]
  have key := foldl_arrSum d g (axisOuter n d c ax.val M)
    (fun idx => (c.getD idx 0 : ℝ) * ∑ q ∈ Finset.range (d + 1),
      ((M.getD q #[]).getD (idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1)) 0 : ℝ)
        * wt d g (idx - idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1) * (d + 1) ^ (n - 1 - ax.val)
            + q * (d + 1) ^ (n - 1 - ax.val)))
    (List.range ((d + 1) ^ n))
    (by
      intro idx hidx out hsz
      have hlt : idx < (d + 1) ^ n := List.mem_range.1 hidx
      unfold axisOuter
      split
      · -- the inner loop accumulates one term per row of the matrix
        obtain ⟨e, he⟩ : ∃ e : Fin n → Fin (d + 1),
            Tensor.flatIndex (d + 1) (fun i => (e i : ℕ)) = idx :=
          ⟨(Tensor.boxEquiv (d + 1) n).symm ⟨idx, hlt⟩, by
            rw [← Tensor.boxEquiv_val, Equiv.apply_symm_apply]⟩
        have hdig : idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1) = (e ax : ℕ) := by
          rw [← he, Tensor.flatIndex_digit]
        have inner := foldl_arrSum d g
          (axisInner M ((d + 1) ^ (n - 1 - ax.val)) (idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1))
            (idx - idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1) * (d + 1) ^ (n - 1 - ax.val))
            (c.getD idx 0))
          (fun q => (((M.getD q #[]).getD (idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1)) 0
              * c.getD idx 0 : ℚ) : ℝ)
            * wt d g (idx - idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1) * (d + 1) ^ (n - 1 - ax.val)
                + q * (d + 1) ^ (n - 1 - ax.val)))
          (List.range (d + 1))
          (by
            intro q hq out hsz
            have hq' : q < d + 1 := List.mem_range.1 hq
            have hj : idx - idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1) * (d + 1) ^ (n - 1 - ax.val)
                + q * (d + 1) ^ (n - 1 - ax.val) < (d + 1) ^ n := by
              rw [hdig, ← he]
              have h := flatIndex_update (d + 1) e ax ⟨q, hq'⟩
              simp only at h
              rw [h]
              exact Tensor.flatIndex_lt _ _
            unfold axisInner
            split
            · exact ⟨by simp [hsz], arrSum_set d g out hsz _ hj _⟩
            · rename_i hm
              have hm0 :
                  (M.getD q #[]).getD (idx / (d + 1) ^ (n - 1 - ax.val) % (d + 1)) 0 = 0 := by
                simpa using hm
              refine ⟨hsz, ?_⟩
              rw [hm0]
              simp)
          out hsz
        refine ⟨inner.1, ?_⟩
        rw [inner.2, list_sum_range, Finset.mul_sum]
        congr 1
        apply Finset.sum_congr rfl
        intro q _
        push_cast
        ring
      · rename_i hc
        have hc0 : c.getD idx 0 = 0 := by simpa using hc
        refine ⟨hsz, ?_⟩
        rw [hc0]
        simp)
    (Array.replicate ((d + 1) ^ n) 0) (by simp)
  rw [key.2, arrSum_replicate, zero_add, list_sum_range, Tensor.sum_range_eq_sum_box,
    arrSum_eq_box]
  apply Finset.sum_congr rfl
  intro e _
  congr 1
  rw [Tensor.flatIndex_digit, ← Finset.mul_prod_erase _ _ (Finset.mem_univ ax),
    Function.update_self, Finset.sum_mul]
  have hrest : ∏ i ∈ Finset.univ.erase ax,
        (Function.update g ax fun p =>
          ∑ q ∈ Finset.range (d + 1), ((M.getD q #[]).getD p 0 : ℝ) * g ax q) i (e i)
      = ∏ i ∈ Finset.univ.erase ax, g i (e i) := by
    apply Finset.prod_congr rfl
    intro i hi
    rw [Function.update_of_ne (Finset.ne_of_mem_erase hi)]
  rw [hrest]
  apply Finset.sum_congr rfl
  intro q hq
  rw [wt_update d g e ax q (Finset.mem_range.1 hq)]
  ring

/-! ### The matrices of the checker -/

theorem foldl_add_range (N : ℕ) (f : ℕ → ℚ) :
    (List.range N).foldl (fun acc t => acc + f t) 0 = ∑ t ∈ Finset.range N, f t := by
  induction N with
  | zero => simp
  | succ N ih => rw [List.range_succ, List.foldl_append, ih, Finset.sum_range_succ]; simp

theorem bernMatrix_get (d i j : ℕ) (hi : i ≤ d) (hj : j ≤ d) :
    ((bernMatrix d).getD i #[]).getD j 0
      = if j ≤ i then (binom i j : ℚ) / (binom d j : ℚ) else 0 := by
  have hi' : i < d + 1 := Nat.lt_succ_of_le hi
  have hj' : j < d + 1 := Nat.lt_succ_of_le hj
  simp [bernMatrix, hi', hj']

theorem shiftMatrix_get (d : ℕ) (lo hi : ℚ) (q p : ℕ) (hq : q ≤ d) (hp : p ≤ d) :
    ((shiftMatrix d lo hi).getD q #[]).getD p 0
      = if q ≤ p then (binom p q : ℚ) * lo ^ (p - q) * (hi - lo) ^ q else 0 := by
  have hq' : q < d + 1 := Nat.lt_succ_of_le hq
  have hp' : p < d + 1 := Nat.lt_succ_of_le hp
  simp [shiftMatrix, hq', hp']

theorem matMul_get (d : ℕ) (A B : RatMatrix) (i j : ℕ) (hi : i ≤ d) (hj : j ≤ d) :
    ((matMul d A B).getD i #[]).getD j 0
      = ∑ t ∈ Finset.range (d + 1), (A.getD i #[]).getD t 0 * (B.getD t #[]).getD j 0 := by
  have hi' : i < d + 1 := Nat.lt_succ_of_le hi
  have hj' : j < d + 1 := Nat.lt_succ_of_le hj
  rw [← foldl_add_range]
  simp [matMul, hi', hj']

/-! ### The two univariate identities -/

/-- The Bernstein polynomial `B_{j,d}(t) = C(d,j) t^j (1-t)^(d-j)`. -/
noncomputable def bern (d j : ℕ) (t : ℝ) : ℝ := (d.choose j : ℝ) * t ^ j * (1 - t) ^ (d - j)

theorem bern_nonneg (d j : ℕ) (t : ℝ) (h0 : 0 ≤ t) (h1 : t ≤ 1) : 0 ≤ bern d j t := by
  unfold bern
  have h := sub_nonneg.2 h1
  positivity

/-- Correctness of the monomial-to-Bernstein matrix on `[0,1]`: the column `k` of `bernMatrix`
holds the Bernstein coefficients of `t^k`, i.e. `t^k = Σ_j C(j,k)/C(d,k) · B_{j,d}(t)`.
(`C(d,j) C(j,k) = C(d,k) C(d-k,j-k)`, then the binomial theorem for `(t + (1-t))^(d-k)`.) -/
theorem bern_inverse (d k : ℕ) (hk : k ≤ d) (t : ℝ) :
    ∑ j ∈ Finset.range (d + 1), (((bernMatrix d).getD j #[]).getD k 0 : ℝ) * bern d j t
      = t ^ k := by
  have hpos : (0 : ℝ) < (d.choose k : ℝ) := by exact_mod_cast Nat.choose_pos hk
  have h1 : ∀ j ∈ Finset.range (d + 1),
      (((bernMatrix d).getD j #[]).getD k 0 : ℝ) * bern d j t
        = if k ≤ j then ((d - k).choose (j - k) : ℝ) * t ^ j * (1 - t) ^ (d - j) else 0 := by
    intro j hj
    have hj' : j ≤ d := Nat.lt_succ_iff.1 (Finset.mem_range.1 hj)
    rw [bernMatrix_get d j k hj' hk]
    split_ifs with hkj
    · have hmul : (d.choose j : ℝ) * (j.choose k : ℝ)
          = (d.choose k : ℝ) * ((d - k).choose (j - k) : ℝ) := by
        exact_mod_cast Nat.choose_mul (n := d) hkj
      simp only [binom_eq_choose, bern]
      push_cast
      rw [show ((j.choose k : ℝ) / (d.choose k : ℝ))
            * ((d.choose j : ℝ) * t ^ j * (1 - t) ^ (d - j))
          = ((d.choose j : ℝ) * (j.choose k : ℝ)) / (d.choose k : ℝ)
            * (t ^ j * (1 - t) ^ (d - j))
          by ring, hmul, mul_div_cancel_left₀ _ hpos.ne']
      ring
    · simp
  rw [Finset.sum_congr rfl h1, ← Finset.sum_filter]
  have hfilter : (Finset.range (d + 1)).filter (fun j => k ≤ j) = Finset.Ico k (d + 1) := by
    ext j
    simp only [Finset.mem_filter, Finset.mem_range, Finset.mem_Ico]
    omega
  rw [hfilter, Finset.sum_Ico_eq_sum_range]
  have h2 : ∀ m ∈ Finset.range (d + 1 - k),
      ((d - k).choose (k + m - k) : ℝ) * t ^ (k + m) * (1 - t) ^ (d - (k + m))
        = t ^ k * (t ^ m * (1 - t) ^ (d - k - m) * ((d - k).choose m : ℝ)) := by
    intro m _
    rw [Nat.add_sub_cancel_left, pow_add, Nat.sub_add_eq]
    ring
  rw [Finset.sum_congr rfl h2, ← Finset.mul_sum]
  have hd : d + 1 - k = (d - k) + 1 := by omega
  rw [hd, ← add_pow]
  simp

/-- Correctness of the shift matrix: the column `p` of `shiftMatrix` holds the monomial
coefficients of `(lo + (hi - lo) t)^p` (binomial theorem). -/
theorem shift_sum (d p : ℕ) (hp : p ≤ d) (lo hi : ℚ) (t : ℝ) :
    ∑ k ∈ Finset.range (d + 1), (((shiftMatrix d lo hi).getD k #[]).getD p 0 : ℝ) * t ^ k
      = ((lo : ℝ) + ((hi : ℝ) - lo) * t) ^ p := by
  have h1 : ∀ k ∈ Finset.range (d + 1),
      (((shiftMatrix d lo hi).getD k #[]).getD p 0 : ℝ) * t ^ k
        = if k ≤ p then (((hi : ℝ) - lo) * t) ^ k * (lo : ℝ) ^ (p - k) * (p.choose k : ℝ)
          else 0 := by
    intro k hk
    rw [shiftMatrix_get d lo hi k p (Nat.lt_succ_iff.1 (Finset.mem_range.1 hk)) hp]
    split_ifs
    · simp only [binom_eq_choose]
      push_cast
      rw [mul_pow]
      ring
    · simp
  rw [Finset.sum_congr rfl h1, ← Finset.sum_filter]
  have hfilter : (Finset.range (d + 1)).filter (fun k => k ≤ p) = Finset.range (p + 1) := by
    ext k
    simp only [Finset.mem_filter, Finset.mem_range]
    omega
  rw [hfilter, add_comm (lo : ℝ), add_pow]

/-- The matrix of the checker along one axis, `B · S`: its column `p` holds the Bernstein
coefficients, in `t ∈ [0,1]`, of `(lo + (hi - lo) t)^p`. -/
theorem bernShift_sum (d p : ℕ) (hp : p ≤ d) (lo hi : ℚ) (t : ℝ) :
    ∑ j ∈ Finset.range (d + 1),
        (((matMul d (bernMatrix d) (shiftMatrix d lo hi)).getD j #[]).getD p 0 : ℝ) * bern d j t
      = ((lo : ℝ) + ((hi : ℝ) - lo) * t) ^ p := by
  have h1 : ∀ j ∈ Finset.range (d + 1),
      (((matMul d (bernMatrix d) (shiftMatrix d lo hi)).getD j #[]).getD p 0 : ℝ) * bern d j t
        = ∑ k ∈ Finset.range (d + 1),
            (((shiftMatrix d lo hi).getD k #[]).getD p 0 : ℝ)
              * ((((bernMatrix d).getD j #[]).getD k 0 : ℝ) * bern d j t) := by
    intro j hj
    rw [matMul_get d _ _ j p (Nat.lt_succ_iff.1 (Finset.mem_range.1 hj)) hp]
    push_cast
    rw [Finset.sum_mul]
    apply Finset.sum_congr rfl
    intro k _
    ring
  rw [Finset.sum_congr rfl h1, Finset.sum_comm, ← shift_sum d p hp lo hi t]
  apply Finset.sum_congr rfl
  intro k hk
  rw [← Finset.mul_sum, bern_inverse d k (Nat.lt_succ_iff.1 (Finset.mem_range.1 hk)) t]

/-! ### All the axes -/

theorem attach_range'_map (n m : ℕ) (hm : m = n)
    (H : ∀ x : {a // a ∈ List.range' 0 m}, x.1 < n) :
    (List.range' 0 m).attach.map (fun x => (⟨x.1, H x⟩ : Fin n)) = List.finRange n := by
  subst hm
  apply List.ext_getElem
  · simp
  · intro i h1 h2
    simp

/-- `bernsteinCoeffs` applies the matrix `B · S(loᵢ, hiᵢ)` along every axis in turn. -/
theorem bernsteinCoeffs_eq (b : Box n) (p : Tensor n) :
    bernsteinCoeffs b p = (List.finRange n).foldl
      (fun (cur : Array ℚ) (i : Fin n) => applyAxis n p.deg cur i.val
        (matMul p.deg (bernMatrix p.deg) (shiftMatrix p.deg (b.lo i) (b.hi i))))
      (Array.ofFn (n := (p.deg + 1) ^ n) fun i => p.coeffs.getD i.val 0) := by
  unfold bernsteinCoeffs
  simp only [Std.Legacy.Range.forIn'_eq_forIn'_range', Std.Legacy.Range.size,
    List.forIn'_pure_yield_eq_foldl, pure_bind, Id.run_pure]
  rw [← attach_range'_map n ((n - 0 + 1 - 1) / 1) (by simp)
    (fun x => by have := List.mem_range'_1.1 x.2; simp at this; omega), List.foldl_map]

/-- Reading the result of the per-axis passes against `g` is reading the source against the
weights transformed axis by axis. -/
theorem arrSum_foldl_applyAxis (d : ℕ) (Ms : Fin n → RatMatrix) (g : Fin n → ℕ → ℝ)
    (l : List (Fin n)) (hl : l.Nodup) :
    ∀ cur : Array ℚ,
      arrSum d g (l.foldl (fun cur i => applyAxis n d cur i.val (Ms i)) cur)
        = arrSum d (fun i => if i ∈ l then
            (fun p => ∑ q ∈ Finset.range (d + 1), (((Ms i).getD q #[]).getD p 0 : ℝ) * g i q)
            else g i) cur := by
  induction l with
  | nil => intro cur; simp
  | cons a l ih =>
    intro cur
    rw [List.nodup_cons] at hl
    simp only [List.foldl_cons]
    rw [ih hl.2, arrSum_applyAxis]
    congr 1
    funext i
    by_cases hia : i = a
    · subst hia
      simp [hl.1]
    · simp [hia]

/-- [B1] Soundness of the Bernstein test: non-negative Bernstein coefficients over the box `b`
(at the tensor's own degree) imply that the polynomial is non-negative on `b`. -/
theorem bernstein_nonneg (b : Box n) (p : Tensor n) :
    (bernsteinCoeffs b p).all (· ≥ 0) → ∀ x ∈ b.toSet, 0 ≤ p.eval x := by
  intro hall x hx
  -- every control point is `≥ 0`
  have hcp : ∀ j, (0 : ℝ) ≤ ((bernsteinCoeffs b p).getD j 0 : ℝ) := by
    intro j
    by_cases hj : j < (bernsteinCoeffs b p).size
    · have h1 := (Array.all_eq_true_iff_forall_mem.1 hall) _ (Array.getElem_mem hj)
      have h2 : (0 : ℚ) ≤ (bernsteinCoeffs b p)[j] := by simpa using h1
      have h3 : (bernsteinCoeffs b p).getD j 0 = (bernsteinCoeffs b p)[j] := by simp [hj]
      rw [h3]
      exact_mod_cast h2
    · have h3 : (bernsteinCoeffs b p).getD j 0 = 0 := by simp [hj]
      rw [h3]
      simp
  -- the point `x` of the box is `lo + (hi - lo) t` with `t ∈ [0,1]ⁿ`
  have hti : ∀ i, ∃ ti : ℝ, 0 ≤ ti ∧ ti ≤ 1
      ∧ (b.lo i : ℝ) + ((b.hi i : ℝ) - b.lo i) * ti = x i := by
    intro i
    obtain ⟨h1, h2⟩ := hx i
    by_cases hw : (b.hi i : ℝ) - b.lo i = 0
    · refine ⟨0, le_refl _, zero_le_one, ?_⟩
      have hxi : x i = b.lo i := le_antisymm (by linarith) h1
      rw [hxi]
      ring
    · have hwpos : 0 < (b.hi i : ℝ) - b.lo i := lt_of_le_of_ne (by linarith) (Ne.symm hw)
      refine ⟨(x i - b.lo i) / ((b.hi i : ℝ) - b.lo i), div_nonneg (by linarith) hwpos.le,
        (div_le_one hwpos).2 (by linarith), ?_⟩
      field_simp
      ring
  choose t ht using hti
  -- the Bernstein form at `t` is the polynomial at `x`
  have chain : arrSum p.deg (fun i j => bern p.deg j (t i)) (bernsteinCoeffs b p)
      = arrSum p.deg (fun i k => x i ^ k) p.coeffs := by
    rw [bernsteinCoeffs_eq, arrSum_foldl_applyAxis p.deg
      (fun i => matMul p.deg (bernMatrix p.deg) (shiftMatrix p.deg (b.lo i) (b.hi i))) _ _
      (List.nodup_finRange n),
      arrSum_getD_congr p.deg _ _ p.coeffs (by intro j hj; simp [hj])]
    apply arrSum_congr
    intro i k hk
    simp only [List.mem_finRange, ite_true]
    rw [bernShift_sum p.deg k hk, (ht i).2.2]
  rw [eval_eq_arrSum, ← chain]
  unfold arrSum
  apply Finset.sum_nonneg
  intro j _
  apply mul_nonneg (hcp j)
  unfold wt
  apply Finset.prod_nonneg
  intro i _
  exact bern_nonneg _ _ _ (ht i).1 (ht i).2.1

end CnpVerify
