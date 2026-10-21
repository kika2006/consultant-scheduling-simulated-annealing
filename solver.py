"""
Student Consulting Services B.V. - Simulated Annealing Solver
Maximizes net profit for 20 students over 1-day schedule.
"""

import random
import math
import time
import sys
import copy


# ─── File paths ───────────────────────────────────────────────────────────────
DRIVE_FILE  = "data/drivingtimes.txt"
ORDERS_FILE = "data/orders.txt"
SOL_FILE    = "sol.txt"

# ─── Constants ────────────────────────────────────────────────────────────────
N_STUDENTS = 20
HQ_NODE = 251          # Maarheeze (0-indexed in driving matrix)
MAX_SHIFT_SEC = 8 * 3600   # 8 hours in seconds
COST_PER_SEC = 60 / 3600   # €60/hr → €/sec

# ─── Data loading ─────────────────────────────────────────────────────────────

def load_data():
    print("Loading driving times...", flush=True)
    dt_lines = open(DRIVE_FILE).readlines()
    n = len(dt_lines)
    drive = []
    for line in dt_lines:
        drive.append(list(map(int, line.split())))
    print(f"  {n}x{n} matrix loaded.", flush=True)

    print("Loading orders...", flush=True)
    orders = []
    with open(ORDERS_FILE) as f:
        f.readline()  # skip header
        for line in f:
            parts = line.strip().split('\t')
            order_id = int(parts[0])
            node_id  = int(parts[2])
            duration = int(parts[5]) * 60
            profit   = int(parts[6])
            can_do   = [int(x) for x in parts[7:7+N_STUDENTS]]
            orders.append({
                'id': order_id,
                'node': node_id,
                'duration': duration,
                'profit': profit,
                'can_do': can_do,
            })
    print(f"  {len(orders)} orders loaded.", flush=True)
    return drive, orders

# ─── Solution representation ───────────────────────────────────────────────────

def route_time(route, orders, drive):
    if not route:
        return 0
    t = drive[HQ_NODE][orders[route[0]]['node']]
    for i in range(len(route)-1):
        t += orders[route[i]]['duration']
        t += drive[orders[route[i]]['node']][orders[route[i+1]]['node']]
    t += orders[route[-1]]['duration']
    t += drive[orders[route[-1]]['node']][HQ_NODE]
    return t

def route_profit(route, orders):
    return sum(orders[o]['profit'] for o in route)

# ─── State class with incremental updates ─────────────────────────────────────

class State:
    def __init__(self, routes, orders, drive):
        self.routes = [list(r) for r in routes]
        self.orders = orders
        self.drive = drive
        self.route_times   = [route_time(r, orders, drive) for r in routes]
        self.route_profits = [route_profit(r, orders) for r in routes]
        self.order_student = {}
        for s, route in enumerate(routes):
            for o in route:
                self.order_student[o] = s

    @property
    def net_profit(self):
        net = 0.0
        for s in range(N_STUDENTS):
            if self.routes[s]:
                net += self.route_profits[s]
                net -= self.route_times[s] * COST_PER_SEC
        return net

    def n_served(self):
        return sum(len(r) for r in self.routes)

    def delta_remove(self, s, pos):
        route = self.routes[s]
        o = route[pos]
        node_o = self.orders[o]['node']
        dur_o  = self.orders[o]['duration']
        prof_o = self.orders[o]['profit']
        if len(route) == 1:
            old_t = self.drive[HQ_NODE][node_o] + dur_o + self.drive[node_o][HQ_NODE]
            new_t = 0
        else:
            prev_node = HQ_NODE if pos == 0 else self.orders[route[pos-1]]['node']
            next_node = HQ_NODE if pos == len(route)-1 else self.orders[route[pos+1]]['node']
            old_t = self.drive[prev_node][node_o] + dur_o + self.drive[node_o][next_node]
            new_t = self.drive[prev_node][next_node]
        dt = new_t - old_t
        return dt, -prof_o

    def delta_insert(self, s, pos, o):
        route = self.routes[s]
        node_o = self.orders[o]['node']
        dur_o  = self.orders[o]['duration']
        prof_o = self.orders[o]['profit']
        if len(route) == 0:
            old_t = 0
            new_t = self.drive[HQ_NODE][node_o] + dur_o + self.drive[node_o][HQ_NODE]
        else:
            prev_node = HQ_NODE if pos == 0 else self.orders[route[pos-1]]['node']
            next_node = HQ_NODE if pos == len(route) else self.orders[route[pos]]['node']
            old_t = self.drive[prev_node][next_node]
            new_t = self.drive[prev_node][node_o] + dur_o + self.drive[node_o][next_node]
        dt = new_t - old_t
        return dt, prof_o

    def apply_remove(self, s, pos):
        dt, dp = self.delta_remove(s, pos)
        o = self.routes[s].pop(pos)
        self.route_times[s]   += dt
        self.route_profits[s] += dp
        del self.order_student[o]

    def apply_insert(self, s, pos, o):
        dt, dp = self.delta_insert(s, pos, o)
        self.routes[s].insert(pos, o)
        self.route_times[s]   += dt
        self.route_profits[s] += dp
        self.order_student[o] = s

    def copy(self):
        st = State.__new__(State)
        st.routes = [list(r) for r in self.routes]
        st.orders = self.orders
        st.drive  = self.drive
        st.route_times   = list(self.route_times)
        st.route_profits = list(self.route_profits)
        st.order_student = dict(self.order_student)
        return st

# ─── Operators ────────────────────────────────────────────────────────────────

def can_student_do(orders, student_idx, order_idx):
    return orders[order_idx]['can_do'][student_idx] == 1

def op_add_order(state, unassigned):
    if not unassigned:
        return None
    o = random.choice(unassigned)
    eligible = [s for s in range(N_STUDENTS) if can_student_do(state.orders, s, o)]
    if not eligible:
        return None
    s = random.choice(eligible)
    pos = random.randint(0, len(state.routes[s]))
    dt, dp = state.delta_insert(s, pos, o)
    if state.route_times[s] + dt > MAX_SHIFT_SEC:
        return None
    return ('add', s, pos, o, dp - dt * COST_PER_SEC)

def op_remove_order(state, unassigned):
    candidates = [s for s in range(N_STUDENTS) if state.routes[s]]
    if not candidates:
        return None
    s = random.choice(candidates)
    pos = random.randint(0, len(state.routes[s])-1)
    dt, dp = state.delta_remove(s, pos)
    return ('remove', s, pos, state.routes[s][pos], dp - dt * COST_PER_SEC)

def op_relocate(state, unassigned):
    candidates = [s for s in range(N_STUDENTS) if state.routes[s]]
    if not candidates:
        return None
    s_from = random.choice(candidates)
    pos_from = random.randint(0, len(state.routes[s_from])-1)
    o = state.routes[s_from][pos_from]
    eligible = [s for s in range(N_STUDENTS)
                if s != s_from and can_student_do(state.orders, s, o)]
    if not eligible:
        return None
    s_to = random.choice(eligible)
    pos_to = random.randint(0, len(state.routes[s_to]))
    dt_rem, dp_rem = state.delta_remove(s_from, pos_from)
    dt_ins, dp_ins = state.delta_insert(s_to, pos_to, o)
    if state.route_times[s_to] + dt_ins > MAX_SHIFT_SEC:
        return None
    delta_profit = (dp_rem + dp_ins) - (dt_rem + dt_ins) * COST_PER_SEC
    return ('relocate', s_from, pos_from, s_to, pos_to, o, delta_profit)

def op_2opt_intra(state, unassigned):
    candidates = [s for s in range(N_STUDENTS) if len(state.routes[s]) >= 3]
    if not candidates:
        return None
    s = random.choice(candidates)
    route = state.routes[s]
    n = len(route)
    i = random.randint(0, n-2)
    j = random.randint(i+1, n-1)
    if i == 0 and j == n-1:
        return None
    def node(pos):
        return state.orders[route[pos]]['node']
    prev_node = HQ_NODE if i == 0 else node(i-1)
    next_node = HQ_NODE if j == n-1 else node(j+1)
    old_cost = state.drive[prev_node][node(i)] + state.drive[node(j)][next_node]
    new_cost = state.drive[prev_node][node(j)] + state.drive[node(i)][next_node]
    dt = new_cost - old_cost
    if state.route_times[s] + dt > MAX_SHIFT_SEC:
        return None
    return ('2opt', s, i, j, -dt * COST_PER_SEC)

def op_swap_intra(state, unassigned):
    candidates = [s for s in range(N_STUDENTS) if len(state.routes[s]) >= 2]
    if not candidates:
        return None
    s = random.choice(candidates)
    route = state.routes[s]
    n = len(route)
    i, j = random.sample(range(n), 2)
    if i > j:
        i, j = j, i
    def node(pos):
        return state.orders[route[pos]]['node']
    prev_i = HQ_NODE if i == 0 else node(i-1)
    next_j = HQ_NODE if j == n-1 else node(j+1)
    if j == i+1:
        old_cost = state.drive[prev_i][node(i)] + state.drive[node(i)][node(j)] + state.drive[node(j)][next_j]
        new_cost = state.drive[prev_i][node(j)] + state.drive[node(j)][node(i)] + state.drive[node(i)][next_j]
    else:
        old_cost = (state.drive[prev_i][node(i)] + state.drive[node(i)][node(i+1)] +
                    state.drive[node(j-1)][node(j)] + state.drive[node(j)][next_j])
        new_cost = (state.drive[prev_i][node(j)] + state.drive[node(j)][node(i+1)] +
                    state.drive[node(j-1)][node(i)] + state.drive[node(i)][next_j])
    dt = new_cost - old_cost
    if state.route_times[s] + dt > MAX_SHIFT_SEC:
        return None
    return ('swap_intra', s, i, j, -dt * COST_PER_SEC)

def op_swap_inter(state, unassigned):
    candidates = [s for s in range(N_STUDENTS) if state.routes[s]]
    if len(candidates) < 2:
        return None
    s1, s2 = random.sample(candidates, 2)
    pos1 = random.randint(0, len(state.routes[s1])-1)
    pos2 = random.randint(0, len(state.routes[s2])-1)
    o1 = state.routes[s1][pos1]
    o2 = state.routes[s2][pos2]
    if not can_student_do(state.orders, s1, o2):
        return None
    if not can_student_do(state.orders, s2, o1):
        return None
    r1, r2 = state.routes[s1], state.routes[s2]
    def edge_cost(route, pos, replacement_node):
        n = len(route)
        prev = HQ_NODE if pos == 0 else state.orders[route[pos-1]]['node']
        nxt  = HQ_NODE if pos == n-1 else state.orders[route[pos+1]]['node']
        return state.drive[prev][replacement_node] + state.drive[replacement_node][nxt]
    dt1 = (edge_cost(r1, pos1, state.orders[o2]['node']) - edge_cost(r1, pos1, state.orders[o1]['node'])
           + state.orders[o2]['duration'] - state.orders[o1]['duration'])
    dt2 = (edge_cost(r2, pos2, state.orders[o1]['node']) - edge_cost(r2, pos2, state.orders[o2]['node'])
           + state.orders[o1]['duration'] - state.orders[o2]['duration'])
    if state.route_times[s1] + dt1 > MAX_SHIFT_SEC:
        return None
    if state.route_times[s2] + dt2 > MAX_SHIFT_SEC:
        return None
    return ('swap_inter', s1, pos1, s2, pos2, o1, o2, dt1, dt2, -(dt1 + dt2) * COST_PER_SEC)

# ─── Apply operations ─────────────────────────────────────────────────────────

def apply_op(state, unassigned, op):
    kind = op[0]
    if kind == 'add':
        _, s, pos, o, _ = op
        state.apply_insert(s, pos, o)
        unassigned.remove(o)
    elif kind == 'remove':
        _, s, pos, o, _ = op
        state.apply_remove(s, pos)
        unassigned.append(o)
    elif kind == 'relocate':
        _, s_from, pos_from, s_to, pos_to, o, _ = op
        state.apply_remove(s_from, pos_from)
        state.apply_insert(s_to, pos_to, o)
    elif kind == '2opt':
        _, s, i, j, _ = op
        state.routes[s][i:j+1] = state.routes[s][i:j+1][::-1]
        state.route_times[s] += op[4] / (-COST_PER_SEC)
    elif kind == 'swap_intra':
        _, s, i, j, _ = op
        state.routes[s][i], state.routes[s][j] = state.routes[s][j], state.routes[s][i]
        state.route_times[s] += op[4] / (-COST_PER_SEC)
    elif kind == 'swap_inter':
        _, s1, pos1, s2, pos2, o1, o2, dt1, dt2, _ = op
        state.routes[s1][pos1] = o2
        state.routes[s2][pos2] = o1
        state.route_times[s1] += dt1
        state.route_times[s2] += dt2
        state.order_student[o1] = s2
        state.order_student[o2] = s1

def get_delta(op):
    return op[-1]

# ─── Initial greedy solution ───────────────────────────────────────────────────

def greedy_init(orders, drive):
    routes = [[] for _ in range(N_STUDENTS)]
    route_times = [0] * N_STUDENTS
    order_indices = sorted(range(len(orders)), key=lambda i: -orders[i]['profit'])
    for o in order_indices:
        best_delta = -1e18
        best_s = -1
        best_pos = -1
        for s in range(N_STUDENTS):
            if not can_student_do(orders, s, o):
                continue
            route = routes[s]
            for pos in range(len(route)+1):
                node_o = orders[o]['node']
                dur_o  = orders[o]['duration']
                if len(route) == 0:
                    dt = drive[HQ_NODE][node_o] + dur_o + drive[node_o][HQ_NODE]
                else:
                    prev_node = HQ_NODE if pos == 0 else orders[route[pos-1]]['node']
                    next_node = HQ_NODE if pos == len(route) else orders[route[pos]]['node']
                    dt = (drive[prev_node][node_o] + dur_o + drive[node_o][next_node]
                          - drive[prev_node][next_node])
                if route_times[s] + dt > MAX_SHIFT_SEC:
                    continue
                delta = orders[o]['profit'] - dt * COST_PER_SEC
                if delta > best_delta:
                    best_delta = delta
                    best_s = s
                    best_pos = pos
        if best_s >= 0 and best_delta > 0:
            routes[best_s].insert(best_pos, o)
            route_times[best_s] = route_time(routes[best_s], orders, drive)
    return routes

# ─── Simulated Annealing ───────────────────────────────────────────────────────

def simulated_annealing(orders, drive, time_limit=300):
    print("Building greedy initial solution...", flush=True)
    init_routes = greedy_init(orders, drive)
    state = State(init_routes, orders, drive)
    assigned = set(state.order_student.keys())
    unassigned = [i for i in range(len(orders)) if i not in assigned]

    best_state = state.copy()
    best_profit = state.net_profit
    print(f"Initial profit: €{best_profit:.2f}, serving {state.n_served()} orders", flush=True)

    ops = [op_add_order, op_remove_order, op_relocate, op_2opt_intra, op_swap_intra, op_swap_inter]

    def get_probs(T):
        if T > 5:
            weights = [50, 10, 20, 5, 5, 10]
        elif T > 0.5:
            weights = [30, 8, 30, 20, 5, 7]
        else:
            weights = [15, 5, 25, 35, 8, 12]
        total = sum(weights)
        return [w / total for w in weights]

    T_start = 40.0
    T_end   = 0.1

    start_time = time.time()
    iteration  = 0
    accepted   = 0
    rejected   = 0
    last_print = start_time
    last_save  = start_time

    print("Starting simulated annealing...", flush=True)

    while True:
        elapsed = time.time() - start_time
        if elapsed >= time_limit:
            break

        frac = elapsed / time_limit
        T = T_start * ((T_end / T_start) ** frac)

        probs = get_probs(T)
        op_fn = random.choices(ops, weights=probs)[0]
        op = op_fn(state, unassigned)
        if op is None:
            iteration += 1
            rejected += 1
            continue

        delta = get_delta(op)

        if delta > 0 or random.random() < math.exp(delta / T):
            apply_op(state, unassigned, op)
            accepted += 1
            if state.net_profit > best_profit:
                best_profit = state.net_profit
                best_state = state.copy()
        else:
            rejected += 1

        iteration += 1
        now = time.time()

        if now - last_print >= 3.0:
            elapsed2 = now - start_time
            its_per_sec = iteration / elapsed2 if elapsed2 > 0 else 0
            ratio = accepted / (accepted + rejected) if (accepted + rejected) > 0 else 0
            print(
                f"Iter {iteration:,} | T={T:.3f} | "
                f"Profit €{state.net_profit:.0f} ({state.n_served()} orders) | "
                f"Best €{best_profit:.0f} | "
                f"{its_per_sec:,.0f} it/s | Accept {ratio:.2%}",
                flush=True
            )
            last_print = now
            accepted   = 0
            rejected   = 0

        if best_profit > 0 and now - last_save >= 5.0:
            write_solution(SOL_FILE, best_state, orders)
            last_save = now

    print(f"\nDone! Best profit: €{best_profit:.2f}, {best_state.n_served()} orders served", flush=True)
    return best_state

# ─── Output ───────────────────────────────────────────────────────────────────

def write_solution(filename, state, orders):
    lines = [str(int(state.net_profit))]
    for s in range(N_STUDENTS):
        route = state.routes[s]
        lines.append(str(len(route)))
        for o in route:
            lines.append(str(orders[o]['id']))
    with open(filename, 'w') as f:
        f.write('\n'.join(lines) + '\n')

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    time_limit = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    drive, orders = load_data()
    best = simulated_annealing(orders, drive, time_limit=time_limit)
    write_solution(SOL_FILE, best, orders)
    print(f"Solution written to:  {SOL_FILE}", flush=True)
    print(f"Final profit: €{best.net_profit:.2f}", flush=True)