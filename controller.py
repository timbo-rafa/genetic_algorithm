from ga_parallel import GA, MessageGA
from state import State
import itertools
import time

f=open("main.log", "w")

def qget(q, i):
  print("Main Queue({i})...".format(i=i), end="", file=f)
  r = q.get()
  print("{r}".format(r=r), file=f)
  return r

def evolve_map(ga):
  return ga.evolve()

def run(
#parameters
  exchange_after, stop_after, generations,
#graph parameters
  cities,
#ga parameters
  population_size, elite_size, mutation_probability,
  independent_populations, number_workers, 
  verbose=False, latex=False):
#Checking for valid parameters
  if (exchange_after > generations):
    raise ValueError(
      "Number of generations needed to exchange top individuals must be smaller than " +
      "number of generations.")

#initialize algorithm
  ga = GA(cities, independent_populations, number_workers,
    generations, exchange_after, stop_after,
    population_size=population_size,
    elite_size=elite_size, mutation_probability=mutation_probability)
  independent_populations = ga.independent_populations
#run it (non-blocking)
  proc, pqueue, departure_queues, arrival_queues = ga.evolve()

#state and printing
  s = State(pqueue, independent_populations, population_size, elite_size, mutation_probability,
    exchange_after, stop_after, generations, latex, ga,
    progress=False, start_time=time.perf_counter())
  
#Print parameters  
  if (verbose):
    s.print_parameters()

  s.print_header()
  idle_time = 0
#start evolution asynchronously
  for generation in range(s.generations):
    print("Main({g})...".format(g=generation), file=f)
    s.progress = False
#evolve population for one iteration
    #res = pool.map(evolve_map, s.ga)
    #for sga, r in zip(s.ga, res):
    #  sga.population = r
#check if a fitter individual was born and print its characteristics
    if (s.update_fittest()):
      s.print_state(generation)
    
#Exchange best individuals from each population if it is on proper generation
    if (((generation % exchange_after) == 0) and (independent_populations > 1)
        and generation):
      print("Main exchange...", end="", file=f)
      s.print_exchange(generation)
      for i in range(independent_populations):
        print("receiving immi from {i}...".format(i=i), end="", file=f)
        immigrant = departure_queues[i].get()
        print("Done", file=f)
        for j in range(independent_populations):
          if (i != j):
            arrival_queues[j].put(immigrant)
      
    if (s.progress):
      idle_time = 0
    else:
      idle_time += 1
    if (idle_time == s.stop_after):
      break #generation loop

# Figure out the stop criteria and print stuff accordingly
# Idle for set generations
  if (idle_time == stop_after):
    s.print_halt(generation)

# Max number of generations reached
  if (generation + 1 == generations):
    s.print_stop(generation)

  if (verbose):
    s.print_solution(g.source)

  for ql in [pqueue, departure_queues, arrival_queues]:
    for q in ql:
      q.close()
      q.join_thread()
  for p in proc:
    p.join()

  return s.fittest