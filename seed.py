"""
seed.py — populate the UniShare DB with realistic demo data.

Usage:
  python seed.py            # Add core seed data (skips if users already exist)
  python seed.py --reset    # Wipe all records and re-seed with core data
  python seed.py --full     # --reset + expanded dataset (more users/content)
"""

import sys
from datetime import datetime, timedelta, timezone

from app import create_app
from app.extensions import db
from app.models import (
    User, Listing, Note, StudySession, SessionRSVP,
    Bounty, SavedListing, Rating, Message, Post, PostComment,
)

# ─────────────────────────────────────────────────────────────────
# Core seed data
# ─────────────────────────────────────────────────────────────────

USERS = [
    # (first, last, email, password, xp, rank, bio)
    ("Jessica", "Thompson", "23001001@student.uwa.edu.au", "password123", 2450, "Campus Legend",
     "Final year CompSci student. I love Flask and making things work. Always happy to help juniors."),
    ("Liam",    "Nguyen",   "23001002@student.uwa.edu.au", "password123", 1820, "Campus Legend",
     "CS + Maths double degree. Algorithm nerd. Happy to tutor — just message me."),
    ("Priya",   "Sharma",   "23001003@student.uwa.edu.au", "password123",  870, "Hustler",
     "MATH1012 survivor. Now paying it forward with study notes and group sessions."),
    ("Callum",  "Reid",     "23001004@student.uwa.edu.au", "password123",  640, "Hustler",
     "Systems programming enthusiast. C is life. Ask me about pointers."),
    ("Mei",     "Chen",     "23001005@student.uwa.edu.au", "password123",  410, "Newbie",
     "First year — still finding my feet. Stats and data science stream."),
    ("Oliver",  "Walsh",    "23001006@student.uwa.edu.au", "password123",  290, "Newbie",
     "Bio/Chem student. Looking for study buddies and affordable textbooks."),
    ("Aisha",   "Malik",    "23001007@student.uwa.edu.au", "password123",  150, "Newbie",
     "Marketing major. New to campus, loving it so far. Always down to collaborate."),
    ("Tom",     "Barker",   "23001008@student.uwa.edu.au", "password123",   80, "Newbie",
     "Accounting first year. Anyone selling ACCT1101 notes? Message me!"),
]

LISTINGS = [
    # (seller_idx, title, unit_code, price, condition, description)
    (0, "Agile Web Development 5th Ed.",          "CITS3403", 45.00, "Good",
     "A few highlights in chapter 3, otherwise great condition. Perfect for the project."),
    (0, "Introduction to Algorithms (CLRS)",      "CITS2200", 60.00, "Like new",
     "Used for one semester, no writing. The bible of algorithms."),
    (1, "Computer Networks: A Top-Down Approach", "CITS3002", 38.00, "Acceptable",
     "Cover slightly bent, all pages intact. Great for the networking units."),
    (1, "Operating System Concepts (Dinosaur)",   "CITS2002", 42.00, "Good",
     "Some sticky notes but easily removed. Really helped me understand processes."),
    (2, "Calculus Early Transcendentals 8th Ed.", "MATH1012", 30.00, "Good",
     "Pencil workings in margins, easy to erase. Brilliant reference for the exam."),
    (2, "Linear Algebra and Its Applications",    "MATH2402", 25.00, "Like new",
     "Barely opened — withdrew from unit. Your gain!"),
    (3, "Business Statistics",                    "STAT2401", 20.00, "Acceptable",
     "Spine worn but readable throughout. All problems still legible."),
    (3, "Database System Concepts 7th Ed.",       "CITS3200", 50.00, "New",
     "Bought the wrong edition, never opened. Still in original shrink wrap."),
    (4, "Engineering Mathematics",                "MATH1011", 35.00, "Good",
     "Good condition, a few folded page corners but pages are clean."),
    (5, "Molecular Cell Biology 8th Ed.",         "BIOC2002", 55.00, "Like new",
     "International edition — same content, smaller price. Highly recommend."),
    (6, "Principles of Marketing",                "MKTG1100", 22.00, "Acceptable",
     "Some yellow highlighting throughout. Notes in margins are actually helpful."),
    (7, "Financial Accounting",                   "ACCT1101", 28.00, "Good",
     "Previous owner's name on inside cover. Otherwise clean throughout."),
]

NOTES = [
    # (author_idx, title, unit_code, semester, description, upvotes, cover_image, content_html)
    (0, "CITS3403 Complete Lecture Summary S1",  "CITS3403", "S1 2025",
     "All 12 weeks condensed into 40 pages. Covers Flask, JS, SQL, testing. "
     "Structured by week with key diagrams reproduced in text.",
     47,
     "images/notes/cits3403_web_dev.svg",
     """<h3>Week 1–3: Web Foundations &amp; Flask Routing</h3>
<p>HTTP is a stateless request-response protocol. Every Flask route maps a URL pattern to a Python function via the <code>@app.route()</code> decorator.</p>
<pre><code>@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))</code></pre>

<h3>SQLAlchemy ORM</h3>
<p>Define models as Python classes that inherit from <code>db.Model</code>. Relationships use <code>db.relationship()</code> with <code>back_populates</code> for bidirectional linking.</p>
<ul>
  <li><code>db.session.add(obj)</code> — stage object for insert</li>
  <li><code>db.session.commit()</code> — write pending changes to disk</li>
  <li><code>Model.query.filter_by(x=y).first()</code> — fetch first matching row</li>
  <li><code>Model.query.get_or_404(id)</code> — fetch by PK or raise 404</li>
</ul>

<h3>Week 4–6: JavaScript &amp; the Fetch API</h3>
<p>The Fetch API replaces <code>XMLHttpRequest</code>. Always return JSON from AJAX endpoints and handle errors in the <code>.catch()</code> chain.</p>
<pre><code>fetch('/api/like/' + postId, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
})
.then(r => r.json())
.then(data => {
  if (data.liked) btn.classList.add('active');
  countEl.textContent = data.count;
})
.catch(err => console.error(err));</code></pre>

<h3>Week 7–9: Security Essentials</h3>
<ul>
  <li><strong>SQL injection</strong> — always use the ORM or parameterised queries; never string-concat user input into SQL</li>
  <li><strong>XSS</strong> — escape user-provided HTML before rendering; Jinja2 auto-escapes by default</li>
  <li><strong>CSRF</strong> — add a hidden token to all state-changing POST forms and validate server-side</li>
  <li><strong>Passwords</strong> — never store plaintext; use <code>werkzeug.security.generate_password_hash</code></li>
  <li><strong>Session cookies</strong> — set <code>HttpOnly</code> and <code>Secure</code> flags in production</li>
</ul>

<h3>Week 10–12: Testing Strategy</h3>
<p>Flask exposes a <code>test_client()</code> for integration tests that simulate HTTP requests without running a server.</p>
<ul>
  <li>Use <code>unittest.TestCase</code> as the base class</li>
  <li><code>pytest</code> fixtures handle setup/teardown cleanly</li>
  <li>Aim for ≥ 80% line coverage — measure with <code>coverage.py</code></li>
  <li>Test both happy paths and edge cases (missing fields, auth failures)</li>
</ul>"""),

    (0, "CITS3403 Final Exam Cheat Sheet",       "CITS3403", "S1 2025",
     "One-page A4 summary allowed in exam. Key patterns and gotchas from past papers. "
     "Covers REST, SQL injection, testing strategies.",
     38,
     "images/notes/cits3403_cheatsheet.svg",
     """<h3>HTTP &amp; REST Quick Reference</h3>
<ul>
  <li><code>GET</code> — read resource, idempotent, no body</li>
  <li><code>POST</code> — create, body with payload, not idempotent</li>
  <li><code>PUT</code> — full replace of resource</li>
  <li><code>PATCH</code> — partial update</li>
  <li><code>DELETE</code> — remove resource</li>
</ul>
<p><strong>Status codes:</strong> <code>200 OK</code> · <code>201 Created</code> · <code>302 Redirect</code> · <code>400 Bad Request</code> · <code>401 Unauthorised</code> · <code>403 Forbidden</code> · <code>404 Not Found</code> · <code>500 Server Error</code></p>

<h3>Flask One-liners</h3>
<pre><code>url_for('view_name', param=val)   # always use, never hardcode paths
redirect(url_for('dashboard'))    # redirect after POST
flash('Saved!', 'success')        # flash message
render_template('page.html', data=data)</code></pre>

<h3>SQLAlchemy One-liners</h3>
<pre><code>User.query.get_or_404(uid)
Note.query.filter(Note.unit_code == 'CITS3403').all()
db.session.delete(obj); db.session.commit()</code></pre>

<h3>Security Gotchas (Exam Favourite)</h3>
<ul>
  <li>Raw SQL: always parameterise — <code>db.execute("SELECT * WHERE id=:id", {"id": id})</code></li>
  <li>CSRF token must be validated on every state-changing POST</li>
  <li><code>Markup(user_html)</code> is dangerous — only use with sanitised content</li>
  <li>Password comparison must be constant-time — use <code>check_password_hash()</code></li>
  <li>Never expose stack traces in production (<code>DEBUG = False</code>)</li>
</ul>

<h3>Testing Checklist</h3>
<ul>
  <li>Test every route for both authenticated and unauthenticated access</li>
  <li>Test form validation — missing fields, oversized inputs</li>
  <li>Assert redirect chains complete correctly</li>
  <li>Cover error handlers (404, 500) explicitly</li>
</ul>"""),

    (1, "CITS2200 Algorithm Analysis Notes",     "CITS2200", "S1 2025",
     "Big-O, sorting algorithms, graph traversals with worked examples. "
     "Includes Dijkstra, Bellman-Ford, and dynamic programming patterns.",
     29,
     "images/notes/cits2200_algorithms.svg",
     """<h3>Time Complexity — Big-O Notation</h3>
<p>Big-O describes the upper bound on an algorithm's growth rate as input size <em>n</em> grows. We drop constants and lower-order terms.</p>
<ul>
  <li><code>O(1)</code> — Constant: array index access, hash table lookup</li>
  <li><code>O(log n)</code> — Logarithmic: binary search, balanced BST operations</li>
  <li><code>O(n)</code> — Linear: single-pass scan, linear search</li>
  <li><code>O(n log n)</code> — Merge sort, heap sort, quicksort (average)</li>
  <li><code>O(n²)</code> — Bubble sort, insertion sort, selection sort</li>
  <li><code>O(2ⁿ)</code> — Exponential: naive recursive Fibonacci, subset enumeration</li>
</ul>

<h3>Graph Traversals</h3>
<p><strong>BFS</strong> uses a queue (FIFO) and guarantees shortest path in unweighted graphs. <strong>DFS</strong> uses a stack (or recursion) and is suited for topological sort and cycle detection.</p>
<pre><code>from collections import deque
def bfs(graph, start):
    visited, queue = set(), deque([start])
    while queue:
        v = queue.popleft()
        if v not in visited:
            visited.add(v)
            queue.extend(graph[v] - visited)</code></pre>

<h3>Dijkstra's Shortest Path</h3>
<p>Greedy algorithm for non-negative weighted graphs. Uses a min-priority queue.</p>
<ul>
  <li>Time: <code>O((V + E) log V)</code> with binary heap</li>
  <li>Cannot handle negative edge weights — use Bellman-Ford instead</li>
  <li>Bellman-Ford: <code>O(VE)</code>, detects negative cycles</li>
</ul>

<h3>Dynamic Programming Patterns</h3>
<p>DP solves problems by breaking them into overlapping subproblems and storing results (memoisation / tabulation).</p>
<ul>
  <li><strong>Fibonacci</strong> — classic top-down memoisation example</li>
  <li><strong>Longest Common Subsequence</strong> — 2D table, <code>O(mn)</code></li>
  <li><strong>0/1 Knapsack</strong> — capacity × items table</li>
  <li><strong>Coin Change</strong> — bottom-up DP, minimum coins</li>
</ul>"""),

    (1, "CITS2002 Systems Programming Guide",    "CITS2002", "S2 2024",
     "C pointers, memory management, process management with diagrams. "
     "File I/O section particularly thorough — covers fork/exec/wait.",
     24,
     "images/notes/cits2002_systems.svg",
     """<h3>Pointers &amp; Memory in C</h3>
<p>A pointer stores the <em>address</em> of another variable. Dereferencing reads the value at that address.</p>
<pre><code>int x = 42;
int *ptr = &amp;x;       // ptr holds address of x
printf("%d", *ptr);  // prints 42 — dereference
*ptr = 100;          // modifies x through ptr</code></pre>
<p><strong>Common pointer errors:</strong> dangling pointers (freed memory), buffer overflows, forgetting to check <code>malloc</code> return value.</p>

<h3>Dynamic Memory Allocation</h3>
<ul>
  <li><code>malloc(n)</code> — allocate <em>n</em> bytes, uninitialised</li>
  <li><code>calloc(n, size)</code> — allocate and zero-initialise</li>
  <li><code>realloc(ptr, new_size)</code> — resize allocation</li>
  <li><code>free(ptr)</code> — release memory; always pair with malloc</li>
</ul>
<pre><code>int *arr = malloc(sizeof(int) * n);
if (!arr) { perror("malloc"); exit(EXIT_FAILURE); }
// ... use arr ...
free(arr);</code></pre>

<h3>Process Management</h3>
<p><code>fork()</code> creates a copy of the calling process. The return value tells you which side you're on.</p>
<pre><code>pid_t pid = fork();
if (pid == 0) {
    // child process — pid == 0
    execvp(argv[0], argv);  // replace image
} else if (pid > 0) {
    // parent — pid is child's PID
    waitpid(pid, &status, 0);
} else {
    perror("fork failed");
}</code></pre>

<h3>File I/O &amp; Signals</h3>
<ul>
  <li><code>open() / read() / write() / close()</code> — POSIX syscalls, work with file descriptors</li>
  <li><code>fopen() / fread() / fwrite() / fclose()</code> — C standard library, buffered I/O</li>
  <li><code>signal(SIGINT, handler)</code> — register a signal handler</li>
  <li><code>pipe(fd[2])</code> — create a unidirectional IPC channel between processes</li>
</ul>"""),

    (2, "MATH1012 Calculus Week 1–6 Notes",      "MATH1012", "S1 2025",
     "Limits, derivatives, integrals — clear explanations with worked examples. "
     "Integration by parts and substitution covered in detail.",
     19,
     "images/notes/math1012_calculus.svg",
     """<h3>Limits</h3>
<p>The limit <code>lim(x→a) f(x) = L</code> means f(x) approaches L as x approaches a, regardless of f(a).</p>
<ul>
  <li><strong>L'Hôpital's Rule</strong>: if f/g → 0/0 or ∞/∞, then lim f/g = lim f'/g'</li>
  <li><strong>Squeeze Theorem</strong>: if g(x) ≤ f(x) ≤ h(x) and lim g = lim h = L, then lim f = L</li>
  <li>Continuity requires: f(a) defined, limit exists, and lim(x→a) f(x) = f(a)</li>
</ul>

<h3>Differentiation Rules</h3>
<ul>
  <li><strong>Power Rule</strong>: d/dx [xⁿ] = nxⁿ⁻¹</li>
  <li><strong>Product Rule</strong>: d/dx [uv] = u'v + uv'</li>
  <li><strong>Quotient Rule</strong>: d/dx [u/v] = (u'v − uv') / v²</li>
  <li><strong>Chain Rule</strong>: d/dx [f(g(x))] = f'(g(x)) · g'(x)</li>
</ul>
<p><em>Worked example — Chain Rule:</em> d/dx [sin(x²)] = cos(x²) · 2x</p>

<h3>Integration Techniques</h3>
<p>The fundamental theorem: ∫ₐᵇ f(x) dx = F(b) − F(a), where F is any antiderivative of f.</p>
<ul>
  <li><strong>u-substitution</strong>: let u = g(x), du = g'(x)dx → transforms integrand</li>
  <li><strong>Integration by parts</strong>: ∫ u dv = uv − ∫ v du (use LIATE for choosing u)</li>
  <li><strong>Partial fractions</strong>: decompose rational functions before integrating</li>
</ul>
<pre><code>LIATE priority for u in integration by parts:
  L — Logarithmic   (ln x)
  I — Inverse trig  (arctan x)
  A — Algebraic     (x², x+1)
  T — Trigonometric (sin x, cos x)
  E — Exponential   (eˣ)</code></pre>"""),

    (2, "MATH2402 Linear Algebra Summary",       "MATH2402", "S1 2025",
     "Eigenvalues, vector spaces, matrix decompositions. "
     "All key theorems stated with proofs where they appeared in lectures.",
     15,
     "images/notes/math2402_linear_algebra.svg",
     """<h3>Vector Spaces &amp; Subspaces</h3>
<p>A vector space V over ℝ must satisfy 8 axioms (closure under addition and scalar multiplication, associativity, commutativity, etc.).</p>
<ul>
  <li><strong>Null space</strong> of A: {x ∈ ℝⁿ : Ax = 0} — always a subspace</li>
  <li><strong>Column space</strong> of A: span of A's columns — equals the image of the transformation</li>
  <li><strong>Rank-Nullity Theorem</strong>: rank(A) + nullity(A) = n (number of columns)</li>
</ul>

<h3>Eigenvalues &amp; Eigenvectors</h3>
<p>λ is an eigenvalue of A if Av = λv for some non-zero vector v. Find eigenvalues by solving det(A − λI) = 0.</p>
<pre><code>Steps to find eigenvalues:
1. Form A − λI
2. Set det(A − λI) = 0  (characteristic polynomial)
3. Solve for λ
4. For each λ, solve (A − λI)v = 0 for eigenvectors</code></pre>

<h3>Key Matrix Decompositions</h3>
<ul>
  <li><strong>LU decomposition</strong>: A = LU where L is lower triangular, U is upper — Gaussian elimination</li>
  <li><strong>Diagonalisation</strong>: A = PDP⁻¹ where D is diagonal (eigenvalues) and P has eigenvectors as columns</li>
  <li><strong>SVD</strong>: A = UΣVᵀ — always exists; Σ contains singular values; used in PCA</li>
  <li><strong>QR decomposition</strong>: A = QR where Q is orthogonal, R is upper triangular</li>
</ul>

<h3>Important Theorems</h3>
<ul>
  <li><strong>Spectral Theorem</strong>: every real symmetric matrix is orthogonally diagonalisable</li>
  <li><strong>Invertible Matrix Theorem</strong>: 15+ equivalent conditions for a matrix being invertible</li>
  <li><strong>Cayley-Hamilton</strong>: every matrix satisfies its own characteristic equation</li>
</ul>"""),

    (3, "STAT2401 R Code Cheatsheet",            "STAT2401", "S2 2024",
     "All the R snippets you need for the practicals in one file. "
     "Covers ggplot2, dplyr, lm, and hypothesis testing functions.",
     33,
     "images/notes/stat2401_stats.svg",
     """<h3>Data Wrangling with dplyr</h3>
<pre><code>library(dplyr)

df %&gt;%
  filter(score &gt; 50) %&gt;%           # row filter
  select(name, score, grade) %&gt;%   # column select
  mutate(pass = score &gt;= 50) %&gt;%   # new column
  arrange(desc(score)) %&gt;%         # sort
  group_by(grade) %&gt;%              # grouping
  summarise(mean_score = mean(score), n = n())</code></pre>

<h3>Visualisation with ggplot2</h3>
<pre><code>library(ggplot2)

# Scatter plot with regression line
ggplot(data, aes(x = hours_studied, y = score)) +
  geom_point(alpha = 0.6) +
  geom_smooth(method = "lm", se = TRUE, colour = "steelblue") +
  labs(title = "Study Hours vs Score", x = "Hours", y = "Score") +
  theme_minimal()

# Bar chart
ggplot(data, aes(x = grade, fill = grade)) +
  geom_bar() + scale_fill_brewer(palette = "Set2")</code></pre>

<h3>Linear Regression</h3>
<pre><code>model &lt;- lm(score ~ hours + sleep, data = df)
summary(model)       # coefficients, R², p-values
confint(model)       # 95% confidence intervals
predict(model, newdata = data.frame(hours=8, sleep=7))</code></pre>

<h3>Hypothesis Testing</h3>
<ul>
  <li><code>t.test(x, y, paired=FALSE)</code> — two-sample t-test</li>
  <li><code>chisq.test(table)</code> — chi-squared test of independence</li>
  <li><code>shapiro.test(x)</code> — normality test (p &gt; 0.05 → normal)</li>
  <li><code>aov(y ~ x, data=df)</code> — one-way ANOVA</li>
</ul>
<p><strong>Decision rule</strong>: if p-value &lt; α (usually 0.05), reject H₀.</p>"""),

    (4, "CITS3003 Graphics OpenGL Notes",        "CITS3003", "S1 2025",
     "Week-by-week notes covering shaders, transformations, lighting. "
     "Includes working GLSL fragment and vertex shader examples.",
     11,
     "images/notes/cits3003_graphics.svg",
     """<h3>The OpenGL Pipeline</h3>
<p>Data flows through the GPU pipeline: CPU → Vertex Shader → Rasterisation → Fragment Shader → Framebuffer.</p>
<ul>
  <li><strong>Vertex shader</strong>: runs once per vertex; transforms positions to clip space</li>
  <li><strong>Rasterisation</strong>: interpolates attributes across the triangle's fragments</li>
  <li><strong>Fragment shader</strong>: runs once per pixel; outputs final colour</li>
</ul>

<h3>3D Transformations</h3>
<p>All transformations are 4×4 homogeneous matrices. The Model-View-Projection (MVP) pipeline:</p>
<pre><code>gl_Position = uProjection * uView * uModel * aPosition;
// M: object → world space
// V: world  → camera space
// P: camera → clip space (perspective divide gives NDC)</code></pre>
<ul>
  <li><strong>Translation</strong>: 4th column of matrix</li>
  <li><strong>Rotation</strong>: 3×3 rotation sub-matrix using trigonometry</li>
  <li><strong>Scale</strong>: diagonal elements of the 3×3 block</li>
</ul>

<h3>GLSL Shader Examples</h3>
<pre><code>// Vertex shader
attribute vec4 aPosition;
attribute vec3 aNormal;
uniform mat4 uMVP;
varying vec3 vNormal;

void main() {
  gl_Position = uMVP * aPosition;
  vNormal = aNormal;
}

// Fragment shader — Phong diffuse
varying vec3 vNormal;
uniform vec3 uLightDir;
void main() {
  float diff = max(dot(normalize(vNormal), uLightDir), 0.0);
  gl_FragColor = vec4(vec3(diff), 1.0);
}</code></pre>

<h3>Phong Lighting Model</h3>
<ul>
  <li><strong>Ambient</strong>: constant background light — <code>Iₐ · kₐ</code></li>
  <li><strong>Diffuse</strong>: Lambert's law — <code>Iᵈ · kᵈ · max(N·L, 0)</code></li>
  <li><strong>Specular</strong>: shiny highlight — <code>Iₛ · kₛ · max(R·V, 0)ⁿ</code></li>
</ul>"""),

    (5, "BIOC2002 Protein Synthesis Summary",    "BIOC2002", "S1 2025",
     "Transcription → translation, with annotated diagrams. "
     "Post-translational modifications and protein folding overview.",
     8,
     "images/notes/bioc2002_biochem.svg",
     """<h3>Central Dogma: DNA → RNA → Protein</h3>
<p>Genetic information flows in one direction: DNA is transcribed into mRNA, which is then translated into protein by ribosomes.</p>
<ul>
  <li><strong>Transcription</strong> (nucleus): RNA polymerase reads template strand 3'→5', synthesises mRNA 5'→3'</li>
  <li><strong>mRNA processing</strong>: 5' cap added, 3' poly-A tail added, introns spliced out by spliceosome</li>
  <li><strong>Translation</strong> (ribosome): mRNA codons read 5'→3'; tRNA anticodons deliver amino acids; peptide bond forms</li>
</ul>

<h3>Transcription in Detail</h3>
<ul>
  <li><strong>Initiation</strong>: RNA pol binds promoter (TATA box at -30); transcription factors recruited</li>
  <li><strong>Elongation</strong>: RNA pol unwinds DNA ~10 bp at a time; adds ribonucleotides (A, U, G, C)</li>
  <li><strong>Termination</strong>: poly-A signal (AAUAAA) triggers cleavage and polyadenylation</li>
</ul>

<h3>Translation &amp; the Genetic Code</h3>
<pre><code>Start codon: AUG (Met) — always the initiation codon
Stop codons: UAA, UAG, UGA — release factors trigger termination

Reading frame example:
  mRNA: 5'—AUG·GCU·UAC·GAA·UAA—3'
  AA:      Met·Ala·Tyr·Glu·[stop]</code></pre>

<h3>Post-Translational Modifications (PTMs)</h3>
<ul>
  <li><strong>Phosphorylation</strong>: Ser/Thr/Tyr — kinases add, phosphatases remove; key in signalling</li>
  <li><strong>Glycosylation</strong>: sugar groups added in ER/Golgi; cell surface recognition</li>
  <li><strong>Ubiquitination</strong>: tags proteins for proteasomal degradation</li>
  <li><strong>Protein folding</strong>: chaperones (HSP70/HSP90) prevent misfolding; hydrophobic collapse drives native fold</li>
</ul>"""),

    (6, "MKTG1100 Marketing Mix Notes",          "MKTG1100", "S2 2024",
     "4Ps framework, case studies, and common exam questions. "
     "Real-world examples from Australian brands used throughout.",
     6,
     "images/notes/mktg1100_marketing.svg",
     """<h3>The 4Ps Marketing Mix</h3>
<p>The marketing mix describes how a company controls the four levers of its offering to reach target customers profitably.</p>

<h3>Product</h3>
<ul>
  <li><strong>Core product</strong>: the fundamental benefit (e.g., a phone gives communication)</li>
  <li><strong>Actual product</strong>: features, branding, quality, packaging</li>
  <li><strong>Augmented product</strong>: warranty, after-sales service, delivery</li>
  <li><strong>Product lifecycle</strong>: Introduction → Growth → Maturity → Decline</li>
</ul>

<h3>Price</h3>
<ul>
  <li><strong>Cost-plus</strong>: cost + markup percentage</li>
  <li><strong>Value-based</strong>: what the customer perceives it to be worth</li>
  <li><strong>Penetration</strong>: low price to gain market share quickly (e.g., Spotify free tier)</li>
  <li><strong>Skimming</strong>: high initial price, lower as competition enters (e.g., new iPhone)</li>
</ul>

<h3>Place (Distribution)</h3>
<ul>
  <li><strong>Direct</strong>: manufacturer → consumer (e.g., Apple Stores)</li>
  <li><strong>Indirect</strong>: via intermediaries — wholesalers, retailers</li>
  <li><strong>Omnichannel</strong>: seamless experience across physical and digital — Woolworths, JB Hi-Fi</li>
</ul>

<h3>Promotion</h3>
<ul>
  <li><strong>Advertising</strong>: paid, non-personal — TV, digital, social</li>
  <li><strong>Sales promotion</strong>: short-term incentives — coupons, BOGOF, loyalty points</li>
  <li><strong>Public relations</strong>: earned media, reputation management</li>
  <li><strong>Personal selling</strong>: direct interaction — insurance, B2B contracts</li>
</ul>

<h3>Australian Brand Case Studies</h3>
<ul>
  <li><strong>Bunnings</strong>: everyday low pricing + wide range + destination stores (Place + Price)</li>
  <li><strong>Vegemite</strong>: brand heritage as core differentiation (Product branding)</li>
  <li><strong>Menulog</strong>: heavy social/TV advertising + convenience positioning (Promotion + Place)</li>
</ul>"""),
]

SESSIONS = [
    # (host_idx, title, unit_code, location, days_from_now, max_att, description)
    (0, "CITS3403 Project 2 Sprint Planning",  "CITS3403",
     "Reid Library Level 2, Bay 14",       3,  6,
     "Going through the marking rubric and splitting tasks for the final sprint. "
     "Bring your laptop and your code."),
    (1, "CITS2200 Exam Prep — Algorithms",     "CITS2200",
     "Computer Science Building G.14",     5,  8,
     "Working through past papers together. Bring your notes. "
     "Focus on graph algorithms and dynamic programming."),
    (2, "MATH1012 Calculus Study Group",       "MATH1012",
     "Barry J Marshall Library",           2, 10,
     "Weekly study group, open to anyone struggling with integration. "
     "We go through practice problems and help each other."),
    (3, "CITS2002 Systems Programming Help",   "CITS2002",
     "Reid Library Level 3",               7,  5,
     "Helping with the C assignment — pointers and file I/O. "
     "Small group, come with specific questions."),
    (4, "STAT2401 R Practical Walkthrough",    "STAT2401",
     "Education Building G.21",            1, 12,
     "Running through the week 8 practical before the due date. "
     "Will cover ggplot2 visualisations and regression models."),
    (0, "CITS3403 Flask Backend Q&A",          "CITS3403",
     "Online — Discord link in bio",       4, 20,
     "Open session — ask anything about the Flask backend and SQLite schema. "
     "Recording will be shared in the group chat afterward."),
]

BOUNTIES = [
    # (poster_idx, title, unit_code, reward, description)
    (0, "Need CITS3403 project partner for final sprint", "CITS3403", 0,
     "Looking for one more person to join our group. We have frontend done, need backend help. "
     "Strong Git skills required."),
    (1, "Past exam papers for CITS2200",                 "CITS2200", 10.00,
     "Will pay $10 for any past CITS2200 exam papers from 2022 or earlier. "
     "PDFs or photos both fine."),
    (2, "Tutor needed for MATH1012 — $30/hr",            "MATH1012", 30.00,
     "Struggling with integration techniques. Need 2–3 sessions before the exam. "
     "Can meet on campus or online."),
    (3, "Anyone selling a CITS3002 textbook?",           "CITS3002", 0,
     "Need the Tanenbaum networking book ASAP. Can pick up anywhere on campus. "
     "Happy to pay fair price."),
    (4, "Proofread my ENGL1000 essay — $15",             "ENGL1000", 15.00,
     "1500 word essay on postcolonial literature. Need feedback within 48 hours. "
     "Focus on argument clarity and referencing."),
    (5, "Lost UWA student card — reward for return",     "",         20.00,
     "Lost near Guild Village on Tuesday. Name on card. No questions asked. "
     "Contact me via messages here."),
    (6, "Looking for ACCT1101 study notes",              "ACCT1101", 5.00,
     "Specifically need notes on the double-entry bookkeeping lectures. "
     "Will pay $5 or trade my MKTG1100 notes."),
]

# RSVPs: (session_idx, [user_indices])
RSVPS = [
    (0, [1, 2, 3]),
    (1, [0, 3, 4, 5]),
    (2, [0, 1, 5, 6, 7]),
    (3, [0, 2]),
    (4, [1, 2, 3, 6]),
    (5, [1, 2, 3, 4, 5, 6, 7]),
]

# Saved listings: (user_idx, [listing_indices])
SAVED = [
    (2, [0, 3, 7]),
    (3, [1, 4]),
    (4, [0, 2, 5]),
    (5, [7, 8]),
    (6, [1, 3]),
    (7, [0, 10]),
]

# Ratings: (rater_idx, rated_idx, listing_idx, score, comment)
RATINGS = [
    (2, 0, 0, 5, "Book was exactly as described, super fast reply!"),
    (3, 0, 1, 5, "Jess is a legend, smooth transaction."),
    (4, 1, 2, 4, "Good condition, took a day to reply but all good."),
    (5, 1, 3, 5, "Perfect, met on campus, no issues."),
    (0, 2, 4, 4, "Minor pencil marks but she was upfront about it."),
    (1, 3, 7, 5, "Brand new as advertised!"),
]

# Messages: (sender_idx, receiver_idx, body, minutes_ago)
MESSAGES = [
    # Liam ↔ Jessica — negotiating the CLRS book
    (1, 0, "Hey Jess! Is the CLRS book still available?",                            200),
    (0, 1, "Yes it is! $60 or best offer. Can meet at Reid Library.",                190),
    (1, 0, "Perfect, how about Thursday 2pm?",                                       185),
    (0, 1, "Works for me! See you at the main entrance.",                            180),
    (1, 0, "Awesome, thanks! See you then.",                                         175),

    # Priya → Jessica — asking about the cheat sheet
    (2, 0, "Hi! Is your CITS3403 cheat sheet still accurate for this semester?",     120),
    (0, 2, "Yep, updated it last week. DM me if you want the PDF.",                  115),
    (2, 0, "That would be amazing, thank you so much!",                              110),
    (0, 2, "No worries — I'll upload it to the notes section tonight.",              105),

    # Callum → Liam — study session
    (3, 1, "Hey Liam, could you help me with the CITS2200 graph traversal stuff?",  300),
    (1, 3, "Sure! I'm running a study session Thursday at CS building. Come along.", 295),
    (3, 1, "I RSVP'd already — looking forward to it!",                             290),
    (1, 3, "Great, bring your notes on BFS/DFS.",                                   285),

    # Mei → Priya — calculus textbook
    (4, 2, "Hi Priya, do you still have the Calculus textbook?",                    400),
    (2, 4, "Sold it last week sorry! But I can share my handwritten notes.",        395),
    (4, 2, "Yes please! That would be super helpful for the exam.",                 390),
    (2, 4, "I'll upload them to the notes section tonight.",                        385),
    (4, 2, "You're a lifesaver, thank you!",                                        380),

    # Oliver → Callum — CITS3002 textbook
    (5, 3, "Callum, do you know anyone with a good CITS3002 textbook?",             500),
    (3, 5, "I have one listed on the marketplace — check it out!",                  495),
    (5, 3, "Oh nice, just saved it. Is the condition really acceptable?",           490),
    (3, 5, "Haha it's fine, just a bit of spine wear. Pages are perfect.",          485),
    (5, 3, "Ok cool, I'll message you if I decide to buy.",                         480),

    # Aisha ↔ Tom — ACCT1101 notes
    (6, 7, "Tom, did you find the ACCT1101 notes yet?",                             600),
    (7, 6, "Not yet! Your listing is the only lead I have.",                        595),
    (6, 7, "I might have some old ones from my first year. I'll check tonight.",    590),
    (7, 6, "That would save my life, thank you!",                                   585),
    (6, 7, "Found them! They're not perfect but should help. I'll upload tomorrow.",580),

    # Jessica → Callum — promoting the Flask Q&A
    (0, 3, "Callum, coming to my Flask Q&A session this week?",                     2880),
    (3, 0, "Definitely! Already RSVP'd. Any pre-reading you recommend?",            2870),
    (0, 3, "Just review the SQLAlchemy ORM docs. We'll work through queries live.", 2860),
    (3, 0, "Perfect. See you there!",                                               2855),

    # Oliver → Jessica — general question
    (5, 0, "Hi Jessica! Is the leaderboard updated weekly or in real-time?",        50),
    (0, 5, "Real-time! XP updates the moment you post, RSVP, or sell something.",   45),
    (5, 0, "Nice, that's motivation to actually contribute. Thanks!",               40),
]


# ─────────────────────────────────────────────────────────────────
# Extra content for --full mode
# ─────────────────────────────────────────────────────────────────

EXTRA_USERS = [
    ("Sophie",   "Anderson", "23001009@student.uwa.edu.au",  "password123", 1100, "Hustler",
     "Psych major with a passion for stats and research methods."),
    ("Marcus",   "Lee",      "23001010@student.uwa.edu.au",  "password123",  760, "Hustler",
     "Software engineer in training. Full-stack by day, gamer by night."),
    ("Zara",     "Khan",     "23001011@student.uwa.edu.au",  "password123",  530, "Newbie",
     "Pre-med student balancing lectures, labs, and life."),
    ("Ethan",    "Brown",    "23001012@student.uwa.edu.au",  "password123",  480, "Newbie",
     "Economics and data science. Love finding patterns in messy data."),
    ("Isabella", "Rossi",    "23001013@student.uwa.edu.au",  "password123",  390, "Newbie",
     "Law/Commerce double degree. Interested in corporate and IP law."),
    ("Noah",     "Williams", "23001014@student.uwa.edu.au",  "password123",  310, "Newbie",
     "Environmental science. Passionate about climate data and sustainability."),
    ("Grace",    "Taylor",   "23001015@student.uwa.edu.au",  "password123",  220, "Newbie",
     "Nursing student. High-pressure, high-reward — love it."),
    ("Jayden",   "Scott",    "23001016@student.uwa.edu.au",  "password123",  170, "Newbie",
     "Mechanical engineering first year. Robotics club member."),
    ("Chloe",    "Martin",   "23001017@student.uwa.edu.au",  "password123",  140, "Newbie",
     "Arts student majoring in history and digital humanities."),
    ("Ryan",     "Hall",     "23001018@student.uwa.edu.au",  "password123",  110, "Newbie",
     "Physics undergrad. If it involves maths, I'm probably interested."),
    ("Ella",     "White",    "23001019@student.uwa.edu.au",  "password123",   90, "Newbie",
     "Biochemistry second year. Lab work is my happy place."),
    ("Daniel",   "Harris",   "23001020@student.uwa.edu.au",  "password123",   60, "Newbie",
     "Commerce first year. Still figuring out what to specialise in."),
]

EXTRA_LISTINGS = [
    # (seller_offset from end of USERS+EXTRA_USERS, title, unit_code, price, condition, desc)
    # seller_offset 0 = Sophie (index 8), 1 = Marcus (9), ...
    (0, "Research Methods in Psychology",        "PSYC2207", 32.00, "Good",      "Used for one semester, minor annotations throughout."),
    (0, "Statistics for Behavioural Sciences",   "PSYC1102", 28.00, "Like new",  "Barely used. Great complement to the lecture slides."),
    (1, "Clean Code by Robert Martin",           "CITS3200", 35.00, "Good",      "Essential reading for any software engineer. A few dog-ears."),
    (1, "JavaScript: The Good Parts",            "CITS3403", 18.00, "Acceptable","Old edition but the core concepts are timeless."),
    (2, "Anatomy & Physiology 10th Ed.",         "SCIE1106", 50.00, "Good",      "Some highlighting in the respiratory chapter."),
    (3, "Principles of Economics 7th Ed.",       "ECON1000", 40.00, "Like new",  "Switched to online resources — this is basically new."),
    (4, "Contract Law in Australia",             "LAWS1113", 55.00, "Good",      "Annotations from tutorial prep — actually helpful notes."),
    (5, "Environmental Systems & Societies",     "SCIE2208", 30.00, "Acceptable","Coffee ring on back cover, content pristine."),
    (6, "Fundamentals of Nursing 9th Ed.",       "NURS1001", 65.00, "Like new",  "International edition. Perfect condition."),
    (7, "Engineering Mechanics: Statics",        "MECH1001", 45.00, "Good",      "A few pencil marks, otherwise very clean."),
    (8, "The Penguin History of the World",      "HIST1001", 15.00, "Acceptable","Well-loved but readable. Great for context."),
    (9, "University Physics 14th Ed.",           "PHYS1002", 58.00, "Good",      "Standard introductory physics. Solid condition."),
]

EXTRA_NOTES = [
    (0, "PSYC1102 Stats for Psych Summary",     "PSYC1102", "S1 2025",
     "Covers t-tests, ANOVA, and regression in plain English. Perfect pre-exam review.", 14),
    (1, "CITS3200 Software Engineering Notes",  "CITS3200", "S1 2025",
     "Agile, UML diagrams, testing patterns, and project management frameworks.", 9),
    (2, "SCIE1106 Anatomy Key Terms Glossary",  "SCIE1106", "S1 2025",
     "700+ anatomical terms with definitions and memory aids.", 7),
    (3, "ECON1000 Micro & Macro Crash Course",  "ECON1000", "S2 2024",
     "Supply/demand, elasticity, GDP — all the essentials without the waffle.", 12),
    (4, "LAWS1113 Contract Law Case List",      "LAWS1113", "S1 2025",
     "All key cases with facts, ratio, and exam relevance rating.", 18),
    (5, "SCIE2208 Climate Systems Notes",       "SCIE2208", "S2 2024",
     "Covers carbon cycles, feedback loops, and climate modelling.", 5),
]

EXTRA_SESSIONS = [
    (0, "PSYC1102 Stats Study Circle",          "PSYC1102",
     "Guild Village Café",                      3,  8,
     "Weekly stats help session. SPSS and Excel both welcome."),
    (1, "Web Dev Portfolio Workshop",           "CITS3200",
     "Computer Science Building G.14",          6, 15,
     "Building your portfolio site together. GitHub Pages or Vercel — your choice."),
    (3, "ECON1000 Tutorial Prep",               "ECON1000",
     "Barry J Marshall Library",                2, 10,
     "Going through this week's tutorial questions before class."),
    (4, "LAWS1113 Case Study Discussion",       "LAWS1113",
     "Law Library Meeting Room 3",              4,  6,
     "Analysing landmark contract law cases. Come prepared to discuss."),
]

EXTRA_BOUNTIES = [
    (0, "Need PSYC study group for finals",      "PSYC1102", 0,
     "Looking for 3–4 people to form a study group before finals. DM me."),
    (1, "Buy my old coding laptop — $400",       "",         400.00,
     "Dell XPS 13, 2022, i7, 16GB RAM. Runs Linux perfectly. Campus pickup."),
    (3, "Help setting up Python environment",    "CITS1401", 10.00,
     "Still getting VS Code and conda working on Windows. 1hr help, $10."),
    (5, "Swap SCIE notes for MATH notes",        "SCIE2208", 0,
     "I have detailed SCIE2208 notes. Looking to trade for MATH2402 notes."),
]


# ─────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)


def reset_db():
    """Delete all records from every table (reverse dependency order)."""
    print("Wiping database records...")
    db.session.execute(db.text("DELETE FROM ratings"))
    db.session.execute(db.text("DELETE FROM saved_listings"))
    db.session.execute(db.text("DELETE FROM session_rsvps"))
    db.session.execute(db.text("DELETE FROM messages"))
    db.session.execute(db.text("DELETE FROM post_comments"))
    db.session.execute(db.text("DELETE FROM post_likes"))
    db.session.execute(db.text("DELETE FROM posts"))
    db.session.execute(db.text("DELETE FROM bounties"))
    db.session.execute(db.text("DELETE FROM sessions"))
    db.session.execute(db.text("DELETE FROM notes"))
    db.session.execute(db.text("DELETE FROM listings"))
    db.session.execute(db.text("DELETE FROM users"))
    db.session.commit()
    print("  ✓ All records removed")


def seed_core():
    """Insert the core 8-user dataset."""
    now = _now()

    # ── Users
    user_objs = []
    for first, last, email, pw, xp, rank, bio in USERS:
        u = User(first_name=first, last_name=last, email=email,
                 xp=xp, rank=rank, bio=bio)
        u.set_password(pw)
        db.session.add(u)
        user_objs.append(u)
    db.session.flush()  # get IDs without committing
    print(f"  ✓ {len(user_objs)} users")

    # ── Listings
    listing_objs = []
    for seller_i, title, unit, price, cond, desc in LISTINGS:
        lst = Listing(seller_id=user_objs[seller_i].id,
                      title=title, unit_code=unit,
                      price=price, condition=cond, description=desc)
        db.session.add(lst)
        listing_objs.append(lst)
    db.session.flush()
    print(f"  ✓ {len(listing_objs)} listings")

    # ── Notes
    for author_i, title, unit, sem, desc, upvotes, cover_img, content_html in NOTES:
        db.session.add(Note(author_id=user_objs[author_i].id,
                            title=title, unit_code=unit,
                            semester=sem, description=desc, upvotes=upvotes,
                            cover_image=cover_img, content_html=content_html))
    db.session.flush()
    print(f"  ✓ {len(NOTES)} notes")

    # ── Study sessions
    session_objs = []
    for host_i, title, unit, location, days, max_att, desc in SESSIONS:
        sess = StudySession(
            host_id=user_objs[host_i].id,
            title=title, unit_code=unit, location=location,
            session_date=now + timedelta(days=days),
            max_attendees=max_att, description=desc,
        )
        db.session.add(sess)
        session_objs.append(sess)
    db.session.flush()
    print(f"  ✓ {len(session_objs)} sessions")

    # ── RSVPs
    rsvp_count = 0
    for sess_i, user_indices in RSVPS:
        for user_i in user_indices:
            db.session.add(SessionRSVP(
                session_id=session_objs[sess_i].id,
                user_id=user_objs[user_i].id,
            ))
            rsvp_count += 1
    db.session.flush()
    print(f"  ✓ {rsvp_count} RSVPs")

    # ── Bounties
    for poster_i, title, unit, reward, desc in BOUNTIES:
        db.session.add(Bounty(poster_id=user_objs[poster_i].id,
                              title=title, unit_code=unit or '',
                              reward=reward, description=desc))
    db.session.flush()
    print(f"  ✓ {len(BOUNTIES)} bounties")

    # ── Saved listings
    saved_count = 0
    for user_i, listing_indices in SAVED:
        for l_i in listing_indices:
            if l_i < len(listing_objs):
                db.session.add(SavedListing(user_id=user_objs[user_i].id,
                                            listing_id=listing_objs[l_i].id))
                saved_count += 1
    db.session.flush()
    print(f"  ✓ {saved_count} saved listings")

    # ── Ratings
    for rater_i, rated_i, listing_i, score, comment in RATINGS:
        db.session.add(Rating(
            rater_id=user_objs[rater_i].id,
            rated_id=user_objs[rated_i].id,
            listing_id=listing_objs[listing_i].id,
            score=score, comment=comment,
        ))
        user_objs[rated_i].rating_sum += score
        user_objs[rated_i].rating_count += 1
    db.session.flush()
    print(f"  ✓ {len(RATINGS)} ratings")

    # ── Messages
    for sender_i, recv_i, body, mins_ago in MESSAGES:
        db.session.add(Message(
            sender_id=user_objs[sender_i].id,
            receiver_id=user_objs[recv_i].id,
            body=body,
            created_at=now - timedelta(minutes=mins_ago),
            read=1,
        ))
    db.session.flush()
    print(f"  ✓ {len(MESSAGES)} messages")

    # ── Posts
    CORE_POSTS = [
        # Dict keys: u (user_idx), ptype, body, hrs_ago, likes
        # Optional: link_url, link_title, link_description, link_image_url
        dict(u=0, ptype='general', hrs_ago=2, likes=14,
             body="Just finished my CITS3200 project — REST API in Flask, full test suite, "
                  "deployed to a VPS. If anyone needs help with Flask or SQLAlchemy, hit me up! 🚀",
             image_path='images/posts/flask_project.svg'),

        dict(u=1, ptype='resource', hrs_ago=5, likes=9,
             body="CLRS 4th edition is absolutely essential if you're doing CITS2200. "
                  "The pseudocode is much cleaner than the 3rd edition and the new chapters on "
                  "randomised algorithms are brilliant. Worth every cent.",
             link_url='https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/',
             link_title='Introduction to Algorithms, Fourth Edition — MIT Press',
             link_description='A comprehensive update of the leading algorithms text, with new chapters, '
                              'revised pseudocode, and expanded coverage of graph algorithms and data structures.',
             link_image_url=None),

        dict(u=2, ptype='event', hrs_ago=8, likes=7,
             body="Study session for STAT2401 this Thursday at Reid Library Level 3, 4–6pm. "
                  "We'll be working through Week 9 problem sets together. All welcome — "
                  "especially if you're struggling with hypothesis testing!"),

        dict(u=3, ptype='news', hrs_ago=12, likes=11,
             body="UWA CS department just announced new electives for 2026 — Machine Learning Systems "
                  "and Distributed Computing. Enrolment opens next Monday. "
                  "Both units look incredible, check the course outline.",
             link_url='https://www.uwa.edu.au/study/courses-and-degrees/by-faculty/faculty-of-engineering-and-mathematical-sciences',
             link_title='Engineering and Mathematical Sciences — The University of Western Australia',
             link_description='Explore undergraduate and postgraduate courses in engineering, computer science, '
                              'mathematics, and data science at UWA.',
             link_image_url=None),

        dict(u=4, ptype='general', hrs_ago=18, likes=5,
             body="Anyone else finding PHIL1001 surprisingly useful for thinking about AI ethics? "
                  "I keep citing it in my CompSci essays lol. The trolley problem hits different "
                  "when you're writing autonomous vehicle code."),

        dict(u=5, ptype='resource', hrs_ago=24, likes=18,
             body="Posted my full MATH1722 notes from Semester 1 — all 12 weeks, typed up in LaTeX "
                  "with worked examples for every major theorem. Check the Notes section. Free to download. "
                  "Upvote if it helps, it motivates me to keep sharing!"),

        dict(u=6, ptype='event', hrs_ago=30, likes=22,
             body="Hackathon at Guild Village this Saturday! Teams of 2–4. "
                  "Theme is 'Smart Campus'. Prizes up to $500 cash and cloud credits. "
                  "Sign up at the Guild desk or drop me a message — still 2 spots on my team.",
             image_path='images/posts/hackathon_poster.svg'),

        dict(u=7, ptype='news', hrs_ago=36, likes=3,
             body="Reminder: HASS enrolment changes apply from next semester. "
                  "Double-check your degree plan in StudentConnect before Week 10 or "
                  "you might end up with a gap in your requirements. Don't get caught out!"),

        dict(u=0, ptype='resource', hrs_ago=48, likes=8,
             body="My CITS3001 revision notes are up — covers all algorithm complexity proofs "
                  "we did in tutorials. Includes a comparison table of time complexities "
                  "that I wish I'd had in Week 1. Should help for the final.",
             link_url='https://github.com',
             link_title='GitHub — Where the world builds software',
             link_description='Millions of developers and companies build, ship, and maintain their software '
                              'on GitHub — the largest and most advanced development platform in the world.',
             link_image_url=None),

        dict(u=1, ptype='general', hrs_ago=60, likes=16,
             body="Hot take: office hours are criminally underused. Just had a 30-min chat with "
                  "the CITS2200 unit coordinator and it cleared up 3 weeks of confusion in one go. "
                  "Most lecturers genuinely love it when students come. Just go."),

        dict(u=2, ptype='event', hrs_ago=72, likes=12,
             body="FREE Python workshop next Tuesday, 1–3pm in CS Building Lab 2. "
                  "Covering data manipulation with pandas and matplotlib. "
                  "Beginners welcome — no prior Python needed. Just bring your laptop.",
             image_path='images/posts/python_workshop.svg'),

        dict(u=3, ptype='news', hrs_ago=96, likes=6,
             body="The Guild is running a textbook buyback scheme this week. "
                  "Drop off your old books at the Guild building for vouchers. "
                  "Good way to clear out last semester's stuff before SWOTVAC."),

        dict(u=4, ptype='resource', hrs_ago=110, likes=4,
             body="Found a great free resource for CITS3003 — the learnopengl.com site covers "
                  "basically everything in the unit with interactive examples. "
                  "Much clearer than the lecture slides for shaders.",
             link_url='https://learnopengl.com',
             link_title='Learn OpenGL — Graphics Programming Tutorials',
             link_description='LearnOpenGL is the ultimate resource for learning modern OpenGL, '
                              'with detailed tutorials covering shaders, lighting, textures, and more.',
             link_image_url=None),
    ]
    post_objs = []
    for p in CORE_POSTS:
        post_objs.append(db.session.add(Post(
            author_id=user_objs[p['u']].id,
            body=p['body'],
            post_type=p['ptype'],
            created_at=now - timedelta(hours=p['hrs_ago']),
            likes_count=p['likes'],
            image_path=p.get('image_path'),
            link_url=p.get('link_url'),
            link_title=p.get('link_title'),
            link_description=p.get('link_description'),
            link_image_url=p.get('link_image_url'),
        )) or Post.query.filter_by(
            author_id=user_objs[p['u']].id,
            body=p['body'],
        ).order_by(Post.id.desc()).first())
    db.session.flush()
    # Re-fetch ordered list after flush
    post_objs = Post.query.order_by(Post.created_at.desc()).limit(len(CORE_POSTS)).all()
    post_objs = list(reversed(post_objs))   # oldest first, matches CORE_POSTS order
    print(f"  ✓ {len(CORE_POSTS)} posts")

    # ── Comments
    # (post_idx, commenter_idx, body, mins_after_post)
    CORE_COMMENTS = [
        # On post 0 (Jessica's Flask project)
        (0, 1, "That's awesome Jess! What database did you use — SQLite or Postgres?", 15),
        (0, 2, "Congrats! Did you deploy on Fly.io or a proper VPS?", 25),
        (0, 3, "Need someone for my CITS3200 project — can I message you?", 40),
        (0, 1, "I'd also love to see the repo if it's public!", 60),

        # On post 1 (Liam's CLRS recommendation)
        (1, 0, "100% agree. The new chapter on approximation algorithms alone is worth it.", 20),
        (1, 4, "Is the 4th edition covered in CITS2200 or do they still use the 3rd?", 35),
        (1, 0, "Check with your unit coordinator — my cohort used 4th ed this semester.", 50),

        # On post 2 (Priya's STAT study session)
        (2, 0, "I'll be there! Struggling with hypothesis testing so this is perfect timing.", 30),
        (2, 5, "What chapter are we up to? Want to review before coming.", 45),
        (2, 0, "Week 9 — two-sample tests and paired comparisons. Bring your R notes!", 60),

        # On post 3 (Callum's UWA news)
        (3, 1, "ML Systems sounds incredible. Finally a proper deep learning elective!", 25),
        (3, 4, "Do you know if it has prerequisites? Hoping CITS2200 counts.", 50),

        # On post 5 (Oliver's MATH notes)
        (5, 2, "Just downloaded — the integration section is incredibly clear. Thank you!", 20),
        (5, 6, "This is gold. The LaTeX formatting makes it so much easier to read.", 40),
        (5, 2, "Happy to help! Let me know if you want me to add more worked examples.", 65),

        # On post 6 (Aisha's hackathon)
        (6, 0, "I'm in! Already have a project idea around lecture room occupancy tracking.", 10),
        (6, 7, "What's the team size limit? Can we enter as a pair?", 20),
        (6, 0, "Yep, teams of 2–4 are all fine. Solo entries are also allowed!", 35),
        (6, 1, "Is there a Discord for participants? Would love to connect beforehand.", 45),

        # On post 9 (Liam's office hours take)
        (9, 0, "This!! I went to office hours for the first time last week and it changed my grade.", 30),
        (9, 3, "Guilty of never going. This is the sign I needed lol", 55),
        (9, 0, "Most coordinators genuinely enjoy it — they want you to get it.", 70),

        # On post 10 (Priya's Python workshop)
        (10, 4, "Will there be recording available for those who can't make it?", 15),
        (10, 5, "Signed up! Can't wait. Do we need to install anything beforehand?", 30),
        (10, 2, "Just Python 3 and a Jupyter notebook — I'll send a setup guide before the session.", 45),
    ]
    for post_idx, user_idx, body, mins in CORE_COMMENTS:
        if post_idx < len(post_objs):
            post = post_objs[post_idx]
            db.session.add(PostComment(
                post_id=post.id,
                author_id=user_objs[user_idx].id,
                body=body,
                created_at=post.created_at + timedelta(minutes=mins),
            ))
            post.comments_count += 1
    db.session.flush()
    print(f"  ✓ {len(CORE_COMMENTS)} comments")

    db.session.commit()
    return user_objs, listing_objs, session_objs


def seed_extra(user_objs, listing_objs, session_objs):
    """Add the expanded dataset on top of core seed."""
    now = _now()

    # ── Extra users
    extra_user_objs = []
    for first, last, email, pw, xp, rank, bio in EXTRA_USERS:
        u = User(first_name=first, last_name=last, email=email,
                 xp=xp, rank=rank, bio=bio)
        u.set_password(pw)
        db.session.add(u)
        extra_user_objs.append(u)
    db.session.flush()
    all_extra = extra_user_objs
    print(f"  ✓ {len(all_extra)} extra users")

    # ── Extra listings (sellers are extra users)
    extra_listing_objs = []
    for seller_offset, title, unit, price, cond, desc in EXTRA_LISTINGS:
        if seller_offset < len(all_extra):
            lst = Listing(seller_id=all_extra[seller_offset].id,
                          title=title, unit_code=unit,
                          price=price, condition=cond, description=desc)
            db.session.add(lst)
            extra_listing_objs.append(lst)
    db.session.flush()
    print(f"  ✓ {len(extra_listing_objs)} extra listings")

    # ── Extra notes
    for author_offset, title, unit, sem, desc, upvotes in EXTRA_NOTES:
        if author_offset < len(all_extra):
            db.session.add(Note(author_id=all_extra[author_offset].id,
                                title=title, unit_code=unit,
                                semester=sem, description=desc, upvotes=upvotes))
    db.session.flush()
    print(f"  ✓ {len(EXTRA_NOTES)} extra notes")

    # ── Extra sessions
    for host_offset, title, unit, location, days, max_att, desc in EXTRA_SESSIONS:
        if host_offset < len(all_extra):
            db.session.add(StudySession(
                host_id=all_extra[host_offset].id,
                title=title, unit_code=unit, location=location,
                session_date=now + timedelta(days=days),
                max_attendees=max_att, description=desc,
            ))
    db.session.flush()
    print(f"  ✓ {len(EXTRA_SESSIONS)} extra sessions")

    # ── Extra bounties
    for poster_offset, title, unit, reward, desc in EXTRA_BOUNTIES:
        if poster_offset < len(all_extra):
            db.session.add(Bounty(poster_id=all_extra[poster_offset].id,
                                  title=title, unit_code=unit or '',
                                  reward=reward, description=desc))
    db.session.flush()
    print(f"  ✓ {len(EXTRA_BOUNTIES)} extra bounties")

    # ── Cross-saves: extra users save some core listings
    cross_saves = [
        (0, 0), (0, 5), (1, 1), (1, 7), (2, 2),
        (3, 4), (4, 6), (5, 8), (6, 9), (7, 0),
    ]
    save_count = 0
    for eu_i, l_i in cross_saves:
        if eu_i < len(all_extra) and l_i < len(listing_objs):
            db.session.add(SavedListing(user_id=all_extra[eu_i].id,
                                        listing_id=listing_objs[l_i].id))
            save_count += 1
    db.session.flush()
    print(f"  ✓ {save_count} extra saved listings")

    # ── Extra messages between extra users and core users
    extra_messages = [
        (all_extra[0].id, user_objs[0].id, "Hi Jessica! Any tips for balancing study and campus life?", 72 * 60),
        (user_objs[0].id, all_extra[0].id, "Honestly? Use UniShare. Post your notes, join sessions, earn XP. It helps!", 71 * 60 + 50),
        (all_extra[0].id, user_objs[0].id, "Already on it. Love the platform!", 71 * 60 + 40),

        (all_extra[1].id, user_objs[1].id, "Marcus here, loved your algorithm notes. Any chance of a CITS3200 version?", 96 * 60),
        (user_objs[1].id, all_extra[1].id, "Working on it! Should be up by end of semester.", 95 * 60 + 55),

        (all_extra[2].id, user_objs[2].id, "Priya, your MATH notes saved my last assignment. Thank you!", 36 * 60),
        (user_objs[2].id, all_extra[2].id, "So glad they helped! Good luck with the exam.", 35 * 60 + 50),

        (all_extra[3].id, user_objs[3].id, "Callum, what IDE do you use for C programming?", 120 * 60),
        (user_objs[3].id, all_extra[3].id, "VS Code with clangd. Absolute game changer. DM me the config.", 119 * 60 + 45),
        (all_extra[3].id, user_objs[3].id, "That's exactly what I needed. Coming to your session for sure!", 119 * 60 + 30),
    ]
    for sender_id, recv_id, body, mins_ago in extra_messages:
        db.session.add(Message(
            sender_id=sender_id, receiver_id=recv_id,
            body=body,
            created_at=now - timedelta(minutes=mins_ago),
            read=1,
        ))
    db.session.flush()
    print(f"  ✓ {len(extra_messages)} extra messages")

    # ── Extra posts
    all_users = user_objs + extra_user_objs
    extra_posts = [
        dict(u_obj=all_users[8],  ptype='resource', hrs_ago=15, likes=7,
             body="Posted CITS1401 Week 1–6 Python notes — beginner-friendly, lots of worked examples. "
                  "Covers loops, functions, file I/O, and basic data structures. Perfect if you're just starting out.",
             link_url='https://docs.python.org/3/tutorial/',
             link_title='The Python Tutorial — Python 3 Documentation',
             link_description='This tutorial introduces the reader informally to the basic concepts and features '
                              'of the Python language and system.',
             link_image_url=None),

        dict(u_obj=all_users[9],  ptype='event', hrs_ago=20, likes=5,
             body="ECON1101 group study at Hackett Hall tomorrow, 10am. "
                  "Covering market structures and game theory. Bring practice papers — "
                  "we'll work through 2023 past exam Q3–Q6 together."),

        dict(u_obj=all_users[10], ptype='general', hrs_ago=28, likes=31,
             body="Just got my first internship offer! If anyone wants tips on technical interviews "
                  "for Perth-based companies, I'm happy to chat. "
                  "The Leetcode grind is real but it works. DM me."),

        dict(u_obj=all_users[11], ptype='news', hrs_ago=40, likes=9,
             body="Library hours extended until midnight during SWOTVAC. "
                  "All floors open, including group study rooms — book early via the portal. "
                  "Level 3 silent zone is first-come-first-served."),
    ]
    for p in extra_posts:
        db.session.add(Post(
            author_id=p['u_obj'].id,
            body=p['body'],
            post_type=p['ptype'],
            created_at=now - timedelta(hours=p['hrs_ago']),
            likes_count=p['likes'],
            link_url=p.get('link_url'),
            link_title=p.get('link_title'),
            link_description=p.get('link_description'),
            link_image_url=p.get('link_image_url'),
        ))
    db.session.flush()
    print(f"  ✓ {len(extra_posts)} extra posts")

    db.session.commit()


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    full_mode  = '--full'  in sys.argv
    reset_mode = '--reset' in sys.argv or full_mode

    app = create_app()
    with app.app_context():
        if reset_mode:
            reset_db()

        # Skip if data already exists and not resetting
        existing = User.query.first()
        if existing and not reset_mode:
            print("Database already has data. Use --reset to wipe and re-seed.")
            sys.exit(0)

        print("Seeding database...")
        user_objs, listing_objs, session_objs = seed_core()

        if full_mode:
            print("Seeding extra content (--full mode)...")
            seed_extra(user_objs, listing_objs, session_objs)

        print("\nDone! Log in with any of these accounts (password: password123):")
        print("  jessica  →  23001001@student.uwa.edu.au  (Campus Legend, 2450 XP)")
        print("  liam     →  23001002@student.uwa.edu.au  (Campus Legend, 1820 XP)")
        print("  priya    →  23001003@student.uwa.edu.au  (Hustler, 870 XP)")
        print("  tom      →  23001008@student.uwa.edu.au  (Newbie, 80 XP)")
        if full_mode:
            print("  sophie   →  23001009@student.uwa.edu.au  (Hustler, 1100 XP)")
            print("  marcus   →  23001010@student.uwa.edu.au  (Hustler, 760 XP)")
