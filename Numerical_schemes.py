import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import quad

#This code was first written with french comments and variables, and translated using LLM

# Definition of the model parameters: They can be modified to test different scenarios.
kappa = 0.1
gamma = 0.05
sigma = 0.01
T = 1.0

# Definition of the number of points for temporal and spatial discretization
nb_steps = 100
nb_points_r = 50
dtau = T / nb_steps
r_min = 0.0
r_max = 0.15
dr = (r_max - r_min) / nb_points_r

# Definition of the meshes
tau_grid = np.linspace(0, T, nb_steps + 1)
t_grid = (T - tau_grid)[::-1]  # Reverse order to obtain the t-grid
r_grid = np.linspace(r_min, r_max, nb_points_r + 1)

# Compute the analytical solution using the closed-form solution.
def compute_B(t):
    return (1 - np.exp(-kappa * (T - t))) / kappa

def compute_A(t):
    b_val = compute_B(t)
    return np.exp((gamma - sigma**2 / (2 * kappa**2)) * (b_val - (T - t)) - (sigma**2 * b_val**2) / (4 * kappa))

def sol_analytique(t, r):
    return compute_A(t) * np.exp(-compute_B(t) * r)

# Evaluate the analytical solution at each grid point for plotting.
analytique_solution = np.zeros((nb_steps + 1, nb_points_r + 1))
for i, t_val in enumerate(t_grid):
    analytique_solution[i, :] = sol_analytique(t_val, r_grid)


def euler_explicit():
    Q = np.ones((nb_steps + 1, nb_points_r + 1))  # Initial condition: Q(0, r) = 1 for all r

    for n in range(nb_steps):
        for i in range(1, nb_points_r):
            dQ_dr = (Q[n, i + 1] - Q[n, i - 1]) / (2 * dr)
            d2Q_dr2 = (Q[n, i + 1] - 2 * Q[n, i] + Q[n, i - 1]) / (dr ** 2)
            L_operator = (kappa * (gamma - r_grid[i]) * dQ_dr
                          + 0.5 * sigma**2 * d2Q_dr2
                          - r_grid[i] * Q[n, i])
            Q[n + 1, i] = Q[n, i] + dtau * L_operator

        # Boundary conditions using the analytical solution
        Q[n + 1, 0] = sol_analytique(T - tau_grid[n + 1], r_min)
        Q[n + 1, nb_points_r] = sol_analytique(T - tau_grid[n + 1], r_max)

    # Convert Q(tau, r) to V(r, t)
    V_explicit = Q[::-1, :]
    return V_explicit

V_explicit = euler_explicit()


def thomas_algorithm(a_vec, b_vec, c_vec, d_vec):
    n = len(b_vec)
    cp = np.zeros(n - 1)
    dp = np.zeros(n)

    # Forward elimination phase
    cp[0] = c_vec[0] / b_vec[0]
    dp[0] = d_vec[0] / b_vec[0]
    for i in range(1, n - 1):
        denom = b_vec[i] - a_vec[i] * cp[i - 1]
        cp[i] = c_vec[i] / denom
        dp[i] = (d_vec[i] - a_vec[i] * dp[i - 1]) / denom

    dp[n - 1] = (d_vec[n - 1] - a_vec[n - 1] * dp[n - 2]) / (b_vec[n - 1] - a_vec[n - 1] * cp[n - 2])

    # Backward substitution phase
    x = np.zeros(n)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]

    return x


def euler_implicit():
    Q = np.ones((nb_steps + 1, nb_points_r + 1))  # Initial condition: Q(0, r) = 1 for all r

    for n in range(nb_steps):
        # Vectors for the tridiagonal system
        a_vec = np.zeros(nb_points_r - 1)
        b_vec = np.zeros(nb_points_r - 1)
        c_vec = np.zeros(nb_points_r - 1)
        d_vec = np.zeros(nb_points_r - 1)

        for i in range(1, nb_points_r):
            idx = i - 1
            # Definition of the coefficients
            alpha = dtau * (0.5 * sigma**2 / (dr**2) - kappa * (gamma - r_grid[i]) / (2 * dr))
            beta  = 1 + dtau * (r_grid[i] + sigma**2 / (dr**2))
            gamma_coef = dtau * (0.5 * sigma**2 / (dr**2) + kappa * (gamma - r_grid[i]) / (2 * dr))

            a_vec[idx] = 0.0 if idx == 0 else -alpha
            b_vec[idx] = beta
            c_vec[idx] = -gamma_coef if idx < (nb_points_r - 2) else 0.0

            # Right-hand side
            d_vec[idx] = Q[n, i]

        # Boundary conditions
        Q[n + 1, 0] = sol_analytique(T - tau_grid[n + 1], r_min)
        Q[n + 1, nb_points_r] = sol_analytique(T - tau_grid[n + 1], r_max)

        d_vec[0] += dtau * (0.5 * sigma**2 / (dr**2) - kappa * (gamma - r_grid[1]) / (2 * dr)) * Q[n + 1, 0]
        d_vec[-1] += dtau * (0.5 * sigma**2 / (dr**2) + kappa * (gamma - r_grid[nb_points_r - 1]) / (2 * dr)) * Q[n + 1, nb_points_r]

        # Solve the tridiagonal system using the Thomas algorithm
        Q_interior = thomas_algorithm(a_vec, b_vec, c_vec, d_vec)

        Q[n + 1, 1:nb_points_r] = Q_interior

    # Convert Q to V
    V_implicit = Q[::-1, :]
    return V_implicit

V_implicit = euler_implicit()


def crank_nicolson():
    r_interior = r_grid[1:nb_points_r]
    coef_a = kappa * (gamma - r_interior) / (2 * dr)
    coef_d = sigma**2 / (2 * dr**2)

    # Definition of all system coefficients
    lower_coeff = -(dtau / 2) * (-coef_a + coef_d)
    diag_coeff  = 1 - (dtau / 2) * (-2 * coef_d - r_interior)
    upper_coeff = -(dtau / 2) * (coef_a + coef_d)
    lower_coeff_rhs = (dtau / 2) * (-coef_a + coef_d)
    diag_coeff_rhs  = 1 + (dtau / 2) * (-2 * coef_d - r_interior)
    upper_coeff_rhs = (dtau / 2) * (coef_a + coef_d)

    # Assembly of matrix A (implicit part)
    A_matrix = np.zeros((nb_points_r - 1, nb_points_r - 1))
    A_matrix[0, 0] = diag_coeff[0]
    if nb_points_r - 1 > 1:
        A_matrix[0, 1] = upper_coeff[0]
    for i in range(1, nb_points_r - 1):
        A_matrix[i, i - 1] = lower_coeff[i]
        A_matrix[i, i] = diag_coeff[i]
        if i < nb_points_r - 2:
            A_matrix[i, i + 1] = upper_coeff[i]
    if nb_points_r - 1 > 1:
        A_matrix[-1, -2] = lower_coeff[-1]
    A_matrix[-1, -1] = diag_coeff[-1]

    Q = np.ones((nb_steps + 1, nb_points_r + 1))
    for n in range(nb_steps):
        # Define boundary conditions
        Q[n + 1, 0] = sol_analytique(T - tau_grid[n + 1], r_min)
        Q[n + 1, nb_points_r] = sol_analytique(T - tau_grid[n + 1], r_max)

        # Right-hand side construction
        d = np.zeros(nb_points_r - 1)
        for i in range(1, nb_points_r):
            idx = i - 1
            d[idx] = diag_coeff_rhs[idx] * Q[n, i]
            if i - 1 >= 0:
                d[idx] += lower_coeff_rhs[idx] * Q[n, i - 1]
            if i + 1 <= nb_points_r:
                d[idx] += upper_coeff_rhs[idx] * Q[n, i + 1]

        # Add boundary conditions for the right-hand side
        d[0] += (dtau / 2) * (-coef_a[0] + coef_d) * Q[n + 1, 0]
        d[-1] += (dtau / 2) * (coef_a[-1] + coef_d) * Q[n + 1, nb_points_r]

        a_vec = np.zeros(nb_points_r - 1)
        b_vec = np.zeros(nb_points_r - 1)
        c_vec = np.zeros(nb_points_r - 1)

        for i in range(nb_points_r - 1):
            if i > 0:
                a_vec[i] = A_matrix[i, i - 1]
            b_vec[i] = A_matrix[i, i]
            if i < nb_points_r - 2:
                c_vec[i] = A_matrix[i, i + 1]

        Q_inner = thomas_algorithm(a_vec, b_vec, c_vec, d)
        Q[n + 1, 1:nb_points_r] = Q_inner

    V_crank = Q[::-1, :]
    return V_crank

V_crank = crank_nicolson()


def fem_method():
    r_nodes = r_grid.copy()
    M_nodes = nb_points_r
    M_global = np.zeros((M_nodes + 1, M_nodes + 1))
    B_global = np.zeros((M_nodes + 1, M_nodes + 1))

    # First, define the phi functions that form a basis for the finite element space, as well as their derivatives.
    def phi(i, r_val):
        if i == 0:
            return (r_nodes[1] - r_val) / dr if (r_nodes[0] <= r_val <= r_nodes[1]) else 0.0
        elif i == M_nodes:
            return (r_val - r_nodes[M_nodes - 1]) / dr if (r_nodes[M_nodes - 1] <= r_val <= r_nodes[M_nodes]) else 0.0
        else:
            if (r_val < r_nodes[i - 1]) or (r_val > r_nodes[i + 1]):
                return 0.0
            if r_val <= r_nodes[i]:
                return (r_val - r_nodes[i - 1]) / dr
            else:
                return (r_nodes[i + 1] - r_val) / dr

    def dphi(i, r_val):
        if i == 0:
            return -1.0 / dr if (r_nodes[0] <= r_val <= r_nodes[1]) else 0.0
        elif i == M_nodes:
            return 1.0 / dr if (r_nodes[M_nodes - 1] <= r_val <= r_nodes[M_nodes]) else 0.0
        else:
            if (r_val < r_nodes[i - 1]) or (r_val > r_nodes[i + 1]):
                return 0.0
            if r_val < r_nodes[i]:
                return 1.0 / dr
            else:
                return -1.0 / dr

    # Define the matrices of the matrix ODE obtained, coefficient by coefficient using the scipy quad function.
    for i in range(M_nodes + 1):
        if i == 0:
            support_i = (r_nodes[0], r_nodes[1])
        elif i == M_nodes:
            support_i = (r_nodes[M_nodes - 1], r_nodes[M_nodes])
        else:
            support_i = (r_nodes[i - 1], r_nodes[i + 1])
        for j in range(M_nodes + 1):
            if j == 0:
                support_j = (r_nodes[0], r_nodes[1])
            elif j == M_nodes:
                support_j = (r_nodes[M_nodes - 1], r_nodes[M_nodes])
            else:
                support_j = (r_nodes[j - 1], r_nodes[j + 1])
            a_int = max(support_i[0], support_j[0])
            b_int = min(support_i[1], support_j[1])
            if a_int < b_int:
                M_global[i, j] = quad(lambda x: phi(i, x) * phi(j, x), a_int, b_int, limit=100)[0]
                B_global[i, j] = quad(lambda x: (kappa * (gamma - x) * dphi(j, x) * phi(i, x)
                                                 - 0.5 * sigma**2 * dphi(j, x) * dphi(i, x)
                                                 - x * phi(j, x) * phi(i, x)),
                                      a_int, b_int, limit=100)[0]

    LHS = M_global - (dtau / 2) * B_global
    RHS = M_global + (dtau / 2) * B_global

    Q = np.ones(M_nodes + 1)  # Initial condition: Q(0, r) = 1 for all r
    Q_all = [Q.copy()]

    for n in range(nb_steps):
        # Boundary conditions
        Q_left = sol_analytique(T - tau_grid[n + 1], r_min)
        Q_right = sol_analytique(T - tau_grid[n + 1], r_max)

        # Right-hand side construction
        b_sys = RHS @ Q
        A_sys = LHS.copy()

        for i in range(1, M_nodes):
            b_sys[i] -= A_sys[i, 0] * Q_left + A_sys[i, M_nodes] * Q_right
            A_sys[i, 0] = 0.0
            A_sys[i, M_nodes] = 0.0
        A_sys[0, :] = 0.0
        A_sys[0, 0] = 1.0
        b_sys[0] = Q_left
        A_sys[M_nodes, :] = 0.0
        A_sys[M_nodes, M_nodes] = 1.0
        b_sys[M_nodes] = Q_right

        Q_new = np.linalg.solve(A_sys, b_sys)
        Q = Q_new.copy()
        Q_all.append(Q.copy())

    Q_all = np.array(Q_all)
    # Convert Q(0, r) to V(r, t)
    V_fem = Q_all[::-1, :]
    return V_fem

V_fem = fem_method()

# Define the grids and format the 3D plots for the solutions
R_mesh, T_mesh = np.meshgrid(r_grid, t_grid)

fig = plt.figure(figsize=(20, 10))

ax1 = fig.add_subplot(231, projection='3d')
ax1.plot_surface(R_mesh, T_mesh, analytique_solution, cmap='viridis', edgecolor='none')
ax1.set_title('Analytical Solution')
ax1.set_xlabel('r')
ax1.set_ylabel('t')
ax1.set_zlabel('V(r,t)')

ax2 = fig.add_subplot(232, projection='3d')
ax2.plot_surface(R_mesh, T_mesh, V_explicit, cmap='Blues', edgecolor='none')
ax2.set_title("Approximation using the Explicit Euler Method")
ax2.set_xlabel('r')
ax2.set_ylabel('t')
ax2.set_zlabel('V(r,t)')

ax3 = fig.add_subplot(233, projection='3d')
ax3.plot_surface(R_mesh, T_mesh, V_implicit, cmap='Reds', edgecolor='none')
ax3.set_title("Approximation using the Implicit Euler Method")
ax3.set_xlabel('r')
ax3.set_ylabel('t')
ax3.set_zlabel('V(r,t)')

ax4 = fig.add_subplot(234, projection='3d')
ax4.plot_surface(R_mesh, T_mesh, V_crank, cmap='coolwarm', edgecolor='none')
ax4.set_title("Approximation using the Crank-Nicolson Method")
ax4.set_xlabel('r')
ax4.set_ylabel('t')
ax4.set_zlabel('V(r,t)')

ax5 = fig.add_subplot(235, projection='3d')
ax5.plot_surface(R_mesh, T_mesh, V_fem, cmap='magma', edgecolor='none')
ax5.set_title("Approximation using the Finite Element Method")
ax5.set_xlabel('r')
ax5.set_ylabel('t')
ax5.set_zlabel('V(r,t)')

plt.tight_layout()
plt.show()


def compute_error(numerical, analytical):
    return np.abs(numerical - analytical)

error_explicit = compute_error(V_explicit, analytique_solution)
error_implicit = compute_error(V_implicit, analytique_solution)
error_crank = compute_error(V_crank, analytique_solution)
error_fem = compute_error(V_fem, analytique_solution)

fig_err = plt.figure(figsize=(20, 10))

ax1_err = fig_err.add_subplot(221, projection='3d')
ax1_err.plot_surface(R_mesh, T_mesh, error_explicit, cmap='magma', edgecolor='none')
ax1_err.set_title("Explicit Euler Error")
ax1_err.set_xlabel("r")
ax1_err.set_ylabel("t")
ax1_err.set_zlabel("Error")

ax2_err = fig_err.add_subplot(222, projection='3d')
ax2_err.plot_surface(R_mesh, T_mesh, error_implicit, cmap='magma', edgecolor='none')
ax2_err.set_title("Implicit Euler Error")
ax2_err.set_xlabel("r")
ax2_err.set_ylabel("t")
ax2_err.set_zlabel("Error")

ax3_err = fig_err.add_subplot(223, projection='3d')
ax3_err.plot_surface(R_mesh, T_mesh, error_crank, cmap='magma', edgecolor='none')
ax3_err.set_title("Crank-Nicolson Error")
ax3_err.set_xlabel("r")
ax3_err.set_ylabel("t")
ax3_err.set_zlabel("Error")

ax4_err = fig_err.add_subplot(224, projection='3d')
ax4_err.plot_surface(R_mesh, T_mesh, error_fem, cmap='magma', edgecolor='none')
ax4_err.set_title("Finite Element Error")
ax4_err.set_xlabel("r")
ax4_err.set_ylabel("t")
ax4_err.set_zlabel("Error")

plt.tight_layout()
plt.show()
