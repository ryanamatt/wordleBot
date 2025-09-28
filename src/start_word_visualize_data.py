import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

INPUT_CSV_FILE = os.path.join("..", "start_word_simulation_data.csv")
OUTPUT_PLOT_FILE = os.path.join("..", "images", "start_word_comparison.png")
SIMULATION_LIMIT = 2315 # Total number of words in the 'possible_answers.txt' file

def load_and_aggregate_data(filename):
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"Error: Input file '{filename}' not found.")
        print("Please ensure you have run 'start_word_simulation.py' successfully to generate the data.")
        return None

    # Filter to get only the successful final guess for each game (where feedback is 'GGGGG')
    # This row contains the final 'guess_num' for a successful game.
    final_guesses_df = df[df['feedback'] == 'GGGGG'].copy()

    # The number of guesses is directly in the 'guess_num' column for the final guess
    final_guesses_df['guesses'] = final_guesses_df['guess_num'].astype(int)

    # 1. Aggregate: Calculate the average guesses and number of solved games per starting word
    summary_df = final_guesses_df.groupby('starting_word')['guesses'].agg(
        mean_guesses='mean',
        games_solved='count'
    ).reset_index()

    # 2. Add total games and calculate win rate
    summary_df['Total Games'] = SIMULATION_LIMIT
    summary_df['Failure Count'] = summary_df['Total Games'] - summary_df['games_solved']
    summary_df['Win Rate (%)'] = (summary_df['games_solved'] / summary_df['Total Games']) * 100
    
    # Sort by the most important metric: average number of guesses (ascending)
    summary_df = summary_df.sort_values(by='mean_guesses', ascending=True)
    
    return summary_df

def plot_results(summary_df, output_filename):
    if summary_df is None or summary_df.empty:
        print("No data to plot.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot the average number of guesses
    bars = ax.bar(
        summary_df['starting_word'].str.upper(),
        summary_df['mean_guesses'],
        color=['#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107'][:len(summary_df)],
        alpha=0.8
    )

    ax.set_title('Wordle Bot Simulation: Comparison of Starting Words', fontsize=16, pad=20)
    ax.set_xlabel('Starting Word', fontsize=14)
    ax.set_ylabel('Average Guesses to Solve (Out of 2315 Words)', fontsize=14)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add data labels for the average guess count
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=10,
                    fontweight='bold')

    # Add a second axis to show the win rate
    ax2 = ax.twinx()
    ax2.plot(
        summary_df['starting_word'].str.upper(), 
        summary_df['Win Rate (%)'], 
        color='black', 
        marker='o', 
        linestyle='--', 
        linewidth=2,
        label='Win Rate (%)'
    )
    ax2.set_ylabel('Win Rate (%)', color='black', fontsize=14)
    ax2.tick_params(axis='y', labelcolor='black')
    # Adjust y-limit for better visualization (min * 0.99 for a bit of padding)
    ax2.set_ylim(summary_df['Win Rate (%)'].min()*0.99, 100.05) 

    # Add annotations for win rate
    for i, rate in enumerate(summary_df['Win Rate (%)']):
        ax2.annotate(f'{rate:.2f}%',
                     (i, rate),
                     textcoords="offset points",
                     xytext=(10, -15),
                     ha='center',
                     fontsize=10,
                     color='black')
        
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_filename)
    print(f"Successfully generated plot: {output_filename}")

def main():
    summary_df = load_and_aggregate_data(INPUT_CSV_FILE)
    if summary_df is not None:
        plot_results(summary_df, OUTPUT_PLOT_FILE)
        # Also save the summary data for user inspection
        summary_df.to_csv("start_word_summary.csv", index=False)
        print("Successfully generated summary CSV: start_word_summary.csv")

if __name__ == "__main__":
    main()