import collections
import time
import os
import csv
import sys
from wordle_bot import load_words, get_feedback, filter_word_list, find_best_guess 
from multiprocessing import Pool

ANSWER_FILE = os.path.join("..", "possible_answers.txt")
MAX_ATTEMPTS = 6
SIMULATION_LIMIT = 2315 # 2315 is Max Number of Words in ANSWER_FILE
NUM_PROCESSES = 10 

OUTPUT_CSV_FILE = os.path.join("..", "csv", "start_word_simulation_data.csv")

STARTING_WORDS = ["raise", "audio", "crane", "slate"] 

def play_game(secret_word, all_answers, all_guesses, starting_guess):
    remaining_possible_words = all_answers
    guess_number = 1
    
    game_history = [] 
    possibilities_before_guess = len(remaining_possible_words)
    
    # Game loop (max 6 guesses)
    while guess_number <= MAX_ATTEMPTS:
        
        # 1. Determine the Best Guess
        if guess_number == 1:
            best_guess = starting_guess
            score = -1.0 # Dummy score for the fixed start
        elif len(remaining_possible_words) == 1:
            best_guess = remaining_possible_words[0]
            score = 0.0
        elif not remaining_possible_words:
            return {'result': -1, 'secret_word': secret_word, 'history': game_history, 'starting_word': starting_guess}
        else:
            # Bot calculates optimal guess based on entropy 
            best_guess, score = find_best_guess(remaining_possible_words, all_guesses, quiet=True)

        # 2. Get Feedback (simulate the response)
        feedback_str = get_feedback(best_guess, secret_word)
        
        # 3. Check for Win
        is_win = (feedback_str == "GGGGG")

        # 4. Filter the Word List (for the next guess)
        remaining_possible_words_after_filter = filter_word_list(remaining_possible_words, best_guess, feedback_str)
        
        # Log the guess details for this turn
        game_history.append({
            'guess_num': guess_number,
            'guess': best_guess,
            'feedback': feedback_str,
            'entropy_score': score, 
            'possibilities_before_guess': possibilities_before_guess, 
            'possibilities_after_filter': len(remaining_possible_words_after_filter),
            'starting_word': starting_guess 
        })

        if is_win:
            return {'result': guess_number, 'secret_word': secret_word, 'history': game_history, 'starting_word': starting_guess}

        # Update state for the next turn
        remaining_possible_words = remaining_possible_words_after_filter
        possibilities_before_guess = len(remaining_possible_words)
        guess_number += 1

    # If the loop finishes without a win (failed)
    return {'result': -1, 'secret_word': secret_word, 'history': game_history, 'starting_word': starting_guess}


def run_simulation_parallel(all_answers, all_guesses, starting_words):
    start_time_total = time.time()
    
    words_to_simulate = all_answers[:SIMULATION_LIMIT]
    num_secret_words = len(words_to_simulate)
    
    print(f"Starting simulation for {num_secret_words} secret words, testing {len(starting_words)} different starting words...")
    print(f"Total games to simulate: {num_secret_words * len(starting_words)} using {NUM_PROCESSES} processes.")

    all_detailed_results = []
    
    try:
        with Pool(NUM_PROCESSES) as pool:
            # Iterate over each starting word sequentially
            for i, starting_word in enumerate(starting_words):
                
                print(f"\n--- Starting simulation {i+1}/{len(starting_words)}: '{starting_word.upper()}' (Testing against all {num_secret_words} words) ---")
                start_time_word = time.time()
                
                # 1. Create argument list for all games for this specific starting word
                args_for_word = []
                for secret_word in words_to_simulate:
                    # Each element is a tuple of arguments for play_game
                    args_for_word.append((secret_word, all_answers, all_guesses, starting_word))
                
                # 2. Run the tasks for this starting word using starmap (blocking call)
                # Since starmap is blocking, all games for this starting word complete here.
                current_word_results = pool.starmap(play_game, args_for_word)
                
                # 3. Process and log the completion
                all_detailed_results.extend(current_word_results)
                
                duration_word = time.time() - start_time_word
                print(f"--- Finished '{starting_word.upper()}' in {duration_word:.2f} seconds at {time.time()}. ---")


    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
        pool.terminate()
        pool.join()
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred during starmap execution: {e}")
        sys.exit(1)
        
    duration_total = time.time() - start_time_total
    
    return all_detailed_results, duration_total

def aggregate_and_report_results(results_list, duration, starting_words):
    print("\n=============================================")
    print("  MULTI-START SIMULATION RESULTS (SUMMARY)   ")
    print("=============================================")
    
    total_games_run = len(results_list)
    print(f"Total Combined Games Simulated: {total_games_run}")
    print(f"Total Time Taken:               {duration:.2f} seconds")
    print("---------------------------------------------")

    # Group results by starting word
    grouped_results = collections.defaultdict(list)
    for game_result in results_list:
        grouped_results[game_result['starting_word']].append(game_result)
        
    # Report for each starting word
    for start_word in starting_words:
        game_results = grouped_results.get(start_word, [])
        if not game_results:
            continue
            
        results = {
            'total_games': len(game_results),
            'total_guesses': 0,
            'wins': 0,
            'failures': 0,
            'guess_counts': collections.defaultdict(int),
        }
        
        for game_result in game_results:
            num_guesses = game_result['result']
            
            if num_guesses != -1 and num_guesses <= MAX_ATTEMPTS:
                results['wins'] += 1
                results['total_guesses'] += num_guesses
                results['guess_counts'][num_guesses] += 1
            else:
                results['failures'] += 1
                
        print(f"\n--- Results for Starting Word: {start_word.upper()} ---")
        
        total_games = results['total_games']
        wins = results['wins']
        
        print(f"  Games Simulated: {total_games}")
        print(f"  Wins/Failures:   {wins} / {results['failures']}")
        
        if wins > 0:
            average_guesses = results['total_guesses'] / wins
            print(f"  Average Guesses: {average_guesses:.3f}")
            
            # Print distribution
            guess_summary = ", ".join([f"{count}: {num_games}" for count, num_games in sorted(results['guess_counts'].items())])
            print(f"  Distribution (Guess: Count): {guess_summary}")
        else:
            print("  No games won.")

    print("\n=============================================")
    
def write_results_to_csv(results_list, filename):
    print(f"\nWriting detailed simulation data to '{filename}'...")
    
    csv_data = []
    
    # Flatten the nested history structure
    for game_result in results_list:
        secret_word = game_result['secret_word']
        num_guesses = game_result['result']
        starting_word = game_result['starting_word']
        
        for turn in game_result['history']:
            row = {
                'secret_word': secret_word,
                'starting_word': starting_word, # New column for analysis
                'game_result': f"{num_guesses} guesses" if num_guesses != -1 else "FAILED",
                'guess_num': turn['guess_num'],
                'guess_word': turn['guess'],
                'feedback': turn['feedback'],
                'entropy_score': turn['entropy_score'],
                'possibilities_before_guess': turn['possibilities_before_guess'],
                'possibilities_after_filter': turn['possibilities_after_filter']
            }
            csv_data.append(row)
            
    if not csv_data:
        print("No simulation data to write.")
        return

    # Define fieldnames, ensuring 'starting_word' is included
    fieldnames = [
        'secret_word',
        'starting_word',
        'game_result',
        'guess_num',
        'guess_word',
        'feedback',
        'entropy_score',
        'possibilities_before_guess',
        'possibilities_after_filter'
    ]

    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        print(f"Successfully wrote {len(csv_data)} guess records to {filename}.")
    except Exception as e:
        print(f"An error occurred while writing the CSV file: {e}")

if __name__ == "__main__":
    # Load all words once
    all_answers, all_guesses = load_words(ANSWER_FILE)

    # Run the simulation across all defined starting words
    detailed_results_list, duration = run_simulation_parallel(all_answers, all_guesses, STARTING_WORDS)
    
    # Aggregate and print the summary report
    aggregate_and_report_results(detailed_results_list, duration, STARTING_WORDS)
    
    # Write the detailed data to a CSV file for analysis
    write_results_to_csv(detailed_results_list, OUTPUT_CSV_FILE)
    
    print("Multi-start simulation complete.")