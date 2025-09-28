import collections
import time
import csv
import os
from wordle_bot import load_words, get_feedback, filter_word_list, find_best_guess, STARTING_GUESS
from multiprocessing import Pool

ANSWER_FILE = os.path.join("..", "possible_answers.txt")
MAX_ATTEMPTS = 6
SIMULATION_LIMIT = 2315 # 2315 Max Number of Words in ANSWER_FILE
NUM_PROCESSES = 10 
OUTPUT_CSV_FILE = os.path.join("..", "csv", "simulation_data.csv") # The new file for detailed results

def play_game(secret_word, all_answers, all_guesses):
    remaining_possible_words = all_answers
    guess_number = 1
    
    # Store the history of the game for analysis.
    # Each entry is a dict containing turn details.
    game_history = [] 
    
    # Initial count of possible words for the first guess
    possibilities_before_guess = len(remaining_possible_words)
    
    # Game loop (max 6 guesses)
    while guess_number <= MAX_ATTEMPTS:
        
        # 1. Determine the Best Guess (using wordle_bot logic)
        if guess_number == 1:
            # Use the hardcoded starting guess
            best_guess = STARTING_GUESS
            score = -1.0 # Score is not calculated for the fixed start
        elif len(remaining_possible_words) == 1:
            # Only one word left - that must be the answer
            best_guess = remaining_possible_words[0]
            score = 0.0
        elif not remaining_possible_words:
            # Should not happen if the word list is correct
            return {'result': -1, 'secret_word': secret_word, 'history': game_history}
        else:
            # The bot calculates the optimal guess based on entropy
            # find_best_guess returns (best_guess, max_entropy_score)
            best_guess, score = find_best_guess(remaining_possible_words, all_guesses, quiet=True)

        # 2. Get Feedback (simulate the response)
        feedback_str = get_feedback(best_guess, secret_word)
        
        # 3. Check for Win Condition
        is_win = (feedback_str == "GGGGG")

        # 4. Filter the Word List
        # This is the list for the *next* guess
        remaining_possible_words_after_filter = filter_word_list(remaining_possible_words, best_guess, feedback_str)
        
        # Log the guess details for this turn
        game_history.append({
            'guess_num': guess_number,
            'guess': best_guess,
            'feedback': feedback_str,
            # The entropy score, indicating effectiveness
            'entropy_score': score, 
            # The size of the set the bot used to calculate the guess
            'possibilities_before_guess': possibilities_before_guess, 
            # The size of the set for the next guess
            'possibilities_after_filter': len(remaining_possible_words_after_filter)
        })

        if is_win:
            return {'result': guess_number, 'secret_word': secret_word, 'history': game_history}

        # Update state for the next turn
        remaining_possible_words = remaining_possible_words_after_filter
        possibilities_before_guess = len(remaining_possible_words)
        guess_number += 1

    # If the loop finishes without a win (failed)
    return {'result': -1, 'secret_word': secret_word, 'history': game_history}

def run_simulation_parallel(all_answers, all_guesses):
    start_time = time.time()
    
    # Limit the number of words to simulate
    words_to_simulate = all_answers[:SIMULATION_LIMIT]
    
    print(f"Starting simulation for {len(words_to_simulate)} secret words using {NUM_PROCESSES} processes...")

    # Prepare arguments for the pool map function
    # We need to pass all_answers and all_guesses to each worker.
    args = [(secret_word, all_answers, all_guesses) for secret_word in words_to_simulate]
    
    with Pool(NUM_PROCESSES) as pool:
        # pool.starmap returns a list of the dictionaries returned by play_game
        results_list = pool.starmap(play_game, args)

    end_time = time.time()
    duration = end_time - start_time
    
    return results_list, duration

def aggregate_and_report_results(results_list, duration):
    results = {
        'total_games': 0,
        'total_guesses': 0,
        'wins': 0,
        'failures': 0,
        'guess_counts': collections.defaultdict(int), # {count: num_games}
        'failed_words': []
    }
    
    for game_result in results_list:
        results['total_games'] += 1
        num_guesses = game_result['result']
        secret_word = game_result['secret_word']
        
        if num_guesses != -1 and num_guesses <= MAX_ATTEMPTS:
            # Win
            results['wins'] += 1
            results['total_guesses'] += num_guesses
            results['guess_counts'][num_guesses] += 1
        else:
            # Failure
            results['failures'] += 1
            results['failed_words'].append(secret_word)


    # --- Print Summary Report ---
    print("\n=============================================")
    print("       SIMULATION RESULTS (SUMMARY)          ")
    print("=============================================")
    
    total_games = results['total_games']
    total_guesses = results['total_guesses']
    wins = results['wins']
    
    print(f"Total Games Simulated: {total_games}")
    print(f"Total Wins:            {wins}")
    print(f"Total Failures:        {results['failures']}")
    print(f"Time Taken:            {duration:.2f} seconds")
    print("---------------------------------------------")

    if wins > 0:
        average_guesses = total_guesses / wins
        print(f"Average Guesses per Win: {average_guesses:.3f}")
        
        # Calculate the distribution of guess counts
        print("\nGuess Distribution:")
        sorted_counts = sorted(results['guess_counts'].items())
        
        for count, num_games in sorted_counts:
            percentage = (num_games / total_games) * 100
            print(f"  {count} Guesses: {num_games} ({percentage:.1f}%)")
    
    if results['failed_words']:
        print("\n--- Failed Words (Took > 6 Guesses) ---")
        print(", ".join(results['failed_words']))
    
    print("=============================================")
    
def write_results_to_csv(results_list, filename):
    print(f"Writing detailed simulation data to '{filename}'...")
    
    csv_data = []
    
    # Flatten the nested history structure
    for game_result in results_list:
        secret_word = game_result['secret_word']
        num_guesses = game_result['result']
        
        for turn in game_result['history']:
            row = {
                'secret_word': secret_word,
                'game_result': f"{num_guesses} guesses" if num_guesses != -1 else "FAILED",
                'guess_num': turn['guess_num'],
                'guess_word': turn['guess'],
                'feedback': turn['feedback'],
                # Key metrics for effectiveness analysis
                'entropy_score': turn['entropy_score'],
                'possibilities_before_guess': turn['possibilities_before_guess'],
                'possibilities_after_filter': turn['possibilities_after_filter']
            }
            csv_data.append(row)
            
    if not csv_data:
        print("No simulation data to write.")
        return

    fieldnames = [
        'secret_word',
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
            # Use DictWriter to easily map dictionary keys to CSV headers
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        print(f"Successfully wrote {len(csv_data)} guess records to {filename}.")
    except Exception as e:
        print(f"An error occurred while writing the CSV file: {e}")

if __name__ == "__main__":
    # Load all words once
    all_answers, all_guesses = load_words(ANSWER_FILE)

    # Run the simulation and collect detailed results
    detailed_results_list, duration = run_simulation_parallel(all_answers, all_guesses)
    
    # Aggregate and print the summary report
    aggregate_and_report_results(detailed_results_list, duration)
    
    # Write the detailed data to a CSV file for analysis
    write_results_to_csv(detailed_results_list, OUTPUT_CSV_FILE)
    
    print("Simulation complete.")
