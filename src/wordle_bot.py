import collections
import time
import math
import os

ANSWER_FILE = os.path.join("..", "possible_answers.txt")

STARTING_GUESS = "raise"

# 'G': Green (Correct Letter, Correct Position)
# 'Y': Yellow (Correct Letter, Wrong Position)
# 'B': Black/Gray (Wrong Letter)
FEEDBACK_CODES = {'G', 'Y', 'B'}

def load_words(filename):
    try:
        with open(filename, 'r') as f:
            words = [line.strip().lower() for line in f if len(line.strip()) == 5 and line.strip().isalpha()]
        return words, words
    except FileNotFoundError:
        print(f"Error: Word file '{filename}' not found.")
        print("Please ensure your word list file is in the same directory and named correctly.")
        exit()

def get_feedback(guess, answer):
    feedback = ['B'] * 5
    answer_counts = collections.Counter(answer)

    # 1. First Pass Mark Greens (G)
    for i in range(5):
        if guess[i] == answer[i]:
            feedback[i] = 'G'
            answer_counts[guess[i]] -= 1

    # 2. Second Pass: Mark Yellows (Y) and Blacks (B)
    for i in range(5):
        if guess[i] == 'G':
            continue

        letter = guess[i]
        if answer_counts[letter] > 0:
            feedback[i] = "Y"
            answer_counts[letter] -= 1
        # Else it reamin 'B' black

    return "".join(feedback)

def filter_word_list(words, guess, feedback):
    return [word for word in words if get_feedback(guess, word) == feedback]

def calculate_entropy(possible_words, guess):
    # Group the possible secret words by the feedback pattern they would generate
    pattern_to_words = collections.defaultdict(list)
    for secret_word in possible_words:
        pattern = get_feedback(guess, secret_word)
        pattern_to_words[pattern].append(secret_word)

    total_words = len(possible_words)
    if total_words <= 1:
        # If 0 or 1 word is left, entropy is 0 (no uncertainty)
        return 0.0

    entropy = 0.0
    for pattern, words_in_bucket in pattern_to_words.items():
        bucket_size = len(words_in_bucket)
        
        # Calculate the probability of this pattern P(p | g)
        probability = bucket_size / total_words
        
        # Entropy contribution: P * log2(1/P)
        # Entropy is the sum of Entropy Contribution
        entropy += probability * math.log2(1.0 / probability)

    # MAXIMIZE this entropy score
    return entropy

def find_best_guess(possible_words, full_guess_pool, quiet=False):
    if not quiet:
        print(f"Calculating best guess among {len(full_guess_pool)} potential words...")
    
    best_score = -1.0
    best_guess = None

    # After the word list has been filtered down significantly (e.g., 50 words or fewer),
    # prioritize checking only the words that could still be the answer.
    # This greatly reduces calculation time in the late game.
    if len(possible_words) <= 50:
        guess_pool = possible_words
        if not quiet:
            print(f"  --> Optimizing: Limiting guess pool to {len(guess_pool)} remaining possibilities.")
    else:
        # Use the full pool of all possible guess words for early, high-information turns
        guess_pool = full_guess_pool
    
    start_time = time.time()

    # Iterate over the potentially reduced guess pool to maximize information gain
    for i, guess in enumerate(guess_pool):
        # Use the entropy calculation
        score = calculate_entropy(possible_words, guess)
        
        # We look for the maximum entropy score
        if score > best_score:
            best_score = score
            best_guess = guess

        # Print progress for long calculations
        if (i + 1) % 500 == 0:
            elapsed = time.time() - start_time
            if not quiet:
                print(f"  Processed {i + 1}/{len(guess_pool)} guesses. Current best: {best_guess} (Entropy: {best_score:.3f}). Time: {elapsed:.2f}s")

    end_time = time.time()
    if not quiet:
        print(f"\nCalculation finished in {end_time - start_time:.2f} seconds.") 
    
    return best_guess, best_score
    
def run_wordle_bot():
    # Load all words accepted as answers and a potential larger pool of guesses
    all_answers, all_guesses = load_words(ANSWER_FILE)
    
    # The set of words that could still be the secret word
    remaining_possible_words = all_answers
    
    guess_number = 1

    print("--- Wordle Optimal Theory Bot ---")
    print(f"Loaded {len(all_answers)} possible answers.")
    print("\n--- Game Start ---\n")

    while True:
        print(f"------------------- Guess {guess_number} -------------------")

        # 1. Determine the Best Guess
        if guess_number == 1:
            best_guess = STARTING_GUESS
            print(f"Recommendation (Pre-calculated): {best_guess.upper()}")
        elif len(remaining_possible_words) == 1:
            best_guess = remaining_possible_words[0]
            print(f"Recommendation (Only one word left): {best_guess.upper()}")
        elif not remaining_possible_words:
             print("ERROR: No words match the feedback you have provided. Check your inputs.")
             break
        else:
            best_guess, best_score = find_best_guess(remaining_possible_words, all_guesses, quiet=False)
            print(f"Recommendation: {best_guess.upper()} (Expected Score: {best_score:.2f})")

        # 2. Get User Input (Guess and Feedback)
        while True:
            # For the bot, we use the recommendation, but allow the user to input a different word
            user_guess = input(f"Enter your guess (or press Enter to use '{best_guess.upper()}'): ").strip().lower()
            if not user_guess:
                user_guess = best_guess
            
            if len(user_guess) != 5:
                print("Guess must be 5 letters long.")
            elif user_guess not in all_guesses:
                # This check ensures the user's input word is a valid guess word
                print("Word not in the valid guess dictionary. Please enter a recognized word.")
            else:
                break

        while True:
            # G: Green, Y: Yellow, B: Black/Gray
            feedback_str = input(f"Enter feedback for '{user_guess.upper()}' (e.g., GBYYB): ").strip().upper()
            if len(feedback_str) != 5 or not all(c in FEEDBACK_CODES for c in feedback_str):
                print("Invalid feedback. Use a 5-letter sequence of 'G' (Green), 'Y' (Yellow), and 'B' (Black/Gray).")
            else:
                break

        # 3. Check for Win Condition
        if feedback_str == "GGGGG":
            print(f"\n--- SUCCESS! Solved in {guess_number} guesses! ---\n")
            break
            
        if guess_number >= 6:
            print("\n--- FAILED! Max guesses reached. The word must have been in the remaining set. ---\n")
            break

        # 4. Filter the Word List
        print("Filtering word list...")
        remaining_possible_words = filter_word_list(remaining_possible_words, user_guess, feedback_str)
        
        # 5. Update State
        num_remaining = len(remaining_possible_words)
        print(f"-> {num_remaining} possible words remaining.")
        
        if num_remaining <= 10:
             print("Remaining possible words: " + ", ".join(remaining_possible_words).upper())
        elif num_remaining > 0:
             print(f"Top 5 remaining words: {', '.join(remaining_possible_words[:5]).upper()}...")

        guess_number += 1
        print("\n" * 2)

if __name__ == "__main__":
    run_wordle_bot()