import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

INPUT_CSV_FILE = os.path.join("..", "csv", "simulation_data.csv")
OUTPUT_PLOT_FILE = os.path.join("..", "images", "simulation_results.png")

def load_and_preprocess_data(filename):
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"Error: Input file '{filename}' not found.")
        print("Please ensure you have run 'simulation.py' successfully to generate the data.")
        return None

    # Convert 'entropy_score' to numeric, coercing errors to NaN
    df['entropy_score'] = pd.to_numeric(df['entropy_score'], errors='coerce')

    # Remove the first guess (guess_num=1) for entropy analysis
    # The first guess is always the hardcoded "raise" with a dummy score (-1.0)
    df_no_first_guess = df[df['guess_num'] > 1].copy()

    # Calculate actual effectiveness of the guess
    # Reduction is the number of words eliminated by the feedback
    df_no_first_guess['word_reduction'] = (
        df_no_first_guess['possibilities_before_guess'] - 
        df_no_first_guess['possibilities_after_filter']
    )
    
    # Calculate relative effectiveness (what percentage of words were eliminated)
    df_no_first_guess['percent_reduction'] = (
        df_no_first_guess['word_reduction'] / df_no_first_guess['possibilities_before_guess']
    )
    
    # Filter out cases where entropy score is 0 or less (e.g., when 1 word remains)
    plot_data = df_no_first_guess[
        (df_no_first_guess['entropy_score'] > 0) & 
        (df_no_first_guess['possibilities_before_guess'] > 1)
    ].copy()

    return plot_data

def plot_analysis_charts(plot_data, output_filename):
    if plot_data is None or plot_data.empty:
        print("No data to plot after preprocessing.")
        return

    fig = plt.figure(figsize=(18, 15))
    fig.suptitle('Wordle Bot Analysis (Starting Word: RAISE)', fontsize=20, fontweight='bold')
    
    # --- (1) Average Reduction vs. Guess Number ---
    ax1 = fig.add_subplot(3, 1, 1)
    # Group by guess number and calculate average word reduction
    avg_reduction_by_guess = plot_data.groupby('guess_num')['percent_reduction'].mean()
    
    ax1.bar(
        avg_reduction_by_guess.index, 
        avg_reduction_by_guess.values * 100, 
        color='skyblue'
    )
    ax1.set_title('(1) Average Percentage of Possible Words Eliminated by Guess Number', fontsize=16)
    ax1.set_xlabel('Guess Number (2nd Guess Onwards)', fontsize=14)
    ax1.set_ylabel('Average Reduction (%)', fontsize=14)
    ax1.set_xticks(avg_reduction_by_guess.index)
    ax1.grid(axis='y', linestyle='--', alpha=0.7)

    # --- (2) Distribution of Entropy Scores ---
    ax2 = fig.add_subplot(3, 1, 2)
    ax2.hist(
        plot_data['entropy_score'], 
        bins=30, 
        color='lightcoral', 
        edgecolor='black'
    )
    ax2.set_title('(2) Distribution of Calculated Entropy Scores', fontsize=16)
    ax2.set_xlabel('Calculated Entropy Score (Bits of Information)', fontsize=14)
    ax2.set_ylabel('Frequency (Number of Guesses)', fontsize=14)
    ax2.grid(axis='y', linestyle='--', alpha=0.7)

    # --- (3) Entropy Score vs. Actual Word Reduction (Effectiveness) ---
    ax3 = fig.add_subplot(3, 1, 3)
    ax3.scatter(
        plot_data['entropy_score'], 
        plot_data['word_reduction'], 
        alpha=0.1, 
        s=10, 
        color='#FF5733'
    )

    # Calculate and plot a simple linear regression line 
    if not plot_data.empty:
        z = np.polyfit(plot_data['entropy_score'], plot_data['word_reduction'], 1)
        p = np.poly1d(z)
        r_squared = plot_data["entropy_score"].corr(plot_data["word_reduction"])**2
        ax3.plot(plot_data['entropy_score'], p(plot_data['entropy_score']), 
                 "b--", label=f'Trendline ($R^2$: {r_squared:.2f})', linewidth=2)
    
    ax3.set_title('(3) Entropy Score (Predicted) vs. Actual Word Reduction (Effectiveness)', fontsize=16)
    ax3.set_xlabel('Calculated Entropy Score (Bits of Information)', fontsize=14)
    ax3.set_ylabel('Actual Word Reduction (Words Eliminated)', fontsize=14)
    ax3.legend()
    ax3.grid(True, linestyle='--', alpha=0.5)

    # Automatically adjust subplot params for tight layout
    plt.tight_layout(rect=[0, 0, 1, 0.96]) # Adjust rect to make space for suptitle
    
    # *** Saves plot to file instead of showing the popup ***
    plt.savefig(output_filename) 
    print(f"Successfully saved analysis plot to {output_filename}")


def main():
    plot_data = load_and_preprocess_data(INPUT_CSV_FILE)
    if plot_data is not None:
        plot_analysis_charts(plot_data, OUTPUT_PLOT_FILE)

if __name__ == "__main__":
    main()