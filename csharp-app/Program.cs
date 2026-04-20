using System;
using System.Collections.Generic;
using System.Drawing;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Text.Json.Serialization;
using System.Linq;

namespace VideoPokerApp
{
    // --- API Models ---
    public class StrategyRequest
    {
        [JsonPropertyName("variant")] public string Variant { get; set; } = "jacks_or_better_9_6";
        [JsonPropertyName("hand")] public List<string> Hand { get; set; } = new();
        [JsonPropertyName("bet")] public int Bet { get; set; } = 5;
        [JsonPropertyName("engine")] public string Engine { get; set; } = "solver";
        [JsonPropertyName("model_path")] public string? ModelPath { get; set; } = null;
    }

    public class StrategyResponse
    {
        [JsonPropertyName("hold")] public List<string> Hold { get; set; } = new();
        [JsonPropertyName("ev")] public double Ev { get; set; }
        [JsonPropertyName("ev_per_coin")] public double EvPerCoin { get; set; }
    }

    public class EvaluateRequest
    {
        [JsonPropertyName("hand")] public List<string> Hand { get; set; } = new();
    }

    public class EvaluateResponse
    {
        [JsonPropertyName("hand_name")] public string HandName { get; set; } = "";
        [JsonPropertyName("rank_value")] public int RankValue { get; set; }
    }

    // --- Main UI Form ---
    public partial class MainForm : Form
    {
        private TextBox handInput;
        private Label strategyResultLabel;
        private Label evLabel;
        private Label evalResultLabel;
        private Button strategyButton;
        private Button evaluateButton;
        private static readonly HttpClient client = new HttpClient();
        private const string BaseUrl = "http://192.168.250.111:8001";

        public MainForm()
        {
            this.Text = "Video Poker Tool";
            this.Size = new Size(450, 380);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;

            var titleLabel = new Label() { 
                Text = "Enter 5-card hand (e.g., Ah Kh Qh Jh 2c):", 
                Location = new Point(20, 20), 
                Size = new Size(400, 20),
                Font = new Font(FontFamily.GenericSansSerif, 10, FontStyle.Bold)
            };

            handInput = new TextBox() { 
                Location = new Point(20, 50), 
                Size = new Size(390, 25), 
                Text = "Ah Kh Qh Jh 2c",
                Font = new Font(FontFamily.GenericSansSerif, 12)
            };

            strategyButton = new Button() { 
                Text = "Get Hold Strategy", 
                Location = new Point(20, 90), 
                Size = new Size(180, 40),
                BackColor = Color.LightBlue,
                FlatStyle = FlatStyle.Flat
            };
            strategyButton.Click += async (s, e) => await FetchStrategy();

            evaluateButton = new Button() { 
                Text = "Evaluate Hand", 
                Location = new Point(210, 90), 
                Size = new Size(180, 40),
                BackColor = Color.LightGreen,
                FlatStyle = FlatStyle.Flat
            };
            evaluateButton.Click += async (s, e) => await FetchEvaluation();

            // --- Strategy Results ---
            var strategyHeader = new Label() { 
                Text = "Recommended Hold Strategy:", 
                Location = new Point(20, 150), 
                Size = new Size(200, 20),
                Font = new Font(FontFamily.GenericSansSerif, 10, FontStyle.Italic)
            };

            strategyResultLabel = new Label() { 
                Location = new Point(20, 175), 
                Size = new Size(390, 30), 
                Text = "-",
                Font = new Font(FontFamily.GenericSansSerif, 14, FontStyle.Bold),
                ForeColor = Color.DarkBlue
            };

            evLabel = new Label() { 
                Location = new Point(20, 210), 
                Size = new Size(390, 20), 
                Text = "",
                Font = new Font(FontFamily.GenericSansSerif, 9)
            };

            // --- Evaluation Results ---
            var evalHeader = new Label() { 
                Text = "Current Hand Value:", 
                Location = new Point(20, 250), 
                Size = new Size(200, 20),
                Font = new Font(FontFamily.GenericSansSerif, 10, FontStyle.Italic)
            };

            evalResultLabel = new Label() { 
                Location = new Point(20, 275), 
                Size = new Size(390, 30), 
                Text = "-",
                Font = new Font(FontFamily.GenericSansSerif, 14, FontStyle.Bold),
                ForeColor = Color.DarkGreen
            };

            this.Controls.AddRange(new Control[] { 
                titleLabel, handInput, strategyButton, evaluateButton, 
                strategyHeader, strategyResultLabel, evLabel,
                evalHeader, evalResultLabel 
            });
        }

        private List<string>? GetInputCards()
        {
            var cards = handInput.Text.Split(new[] { ' ', ',' }, StringSplitOptions.RemoveEmptyEntries);
            if (cards.Length != 5)
            {
                MessageBox.Show("Please enter exactly 5 cards separated by spaces.", "Invalid Hand", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return null;
            }
            return cards.ToList();
        }

        private async Task FetchStrategy()
        {
            var cards = GetInputCards();
            if (cards == null) return;

            try
            {
                strategyButton.Enabled = false;
                strategyResultLabel.Text = "Fetching...";
                
                var request = new StrategyRequest { Hand = cards };
                var response = await client.PostAsJsonAsync($"{BaseUrl}/v1/video-poker/strategy", request);

                if (response.IsSuccessStatusCode)
                {
                    var result = await response.Content.ReadFromJsonAsync<StrategyResponse>();
                    if (result != null)
                    {
                        strategyResultLabel.Text = result.Hold.Count > 0 ? string.Join(", ", result.Hold) : "DISCARD ALL";
                        evLabel.Text = $"Expected Value: {result.Ev:F4} (EV/coin: {result.EvPerCoin:F4})";
                    }
                }
                else
                {
                    var error = await response.Content.ReadAsStringAsync();
                    MessageBox.Show($"API Error: {error}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    strategyResultLabel.Text = "API Error";
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Connection Error: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                strategyResultLabel.Text = "Error";
            }
            finally
            {
                strategyButton.Enabled = true;
            }
        }

        private async Task FetchEvaluation()
        {
            var cards = GetInputCards();
            if (cards == null) return;

            try
            {
                evaluateButton.Enabled = false;
                evalResultLabel.Text = "Evaluating...";
                
                var request = new EvaluateRequest { Hand = cards };
                var response = await client.PostAsJsonAsync($"{BaseUrl}/v1/poker/evaluate", request);

                if (response.IsSuccessStatusCode)
                {
                    var result = await response.Content.ReadFromJsonAsync<EvaluateResponse>();
                    if (result != null)
                    {
                        evalResultLabel.Text = $"{result.HandName} (Rank: {result.RankValue})";
                    }
                }
                else
                {
                    var error = await response.Content.ReadAsStringAsync();
                    MessageBox.Show($"API Error: {error}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    evalResultLabel.Text = "API Error";
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Connection Error: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                evalResultLabel.Text = "Error";
            }
            finally
            {
                evaluateButton.Enabled = true;
            }
        }
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.SetHighDpiMode(HighDpiMode.SystemAware);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }
}
