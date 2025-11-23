"""
Analyze social media content in Data.pdf to identify the cryptocurrency symbol requiring the most attention.

Environment Variables Setup:
Before running this script, please set the following environment variables:

export OPENAI_API_KEY="your-openai-api-key-here"
export OPENAI_MODEL="gpt-4o"
export OPENAI_MAX_TOKENS="2000"

Usage Example:
export OPENAI_API_KEY="sk-proj-..."
export OPENAI_MODEL="gpt-4o"
export OPENAI_MAX_TOKENS="2000"
python service/social_media_analyzer.py
"""

from openai import OpenAI
import os
import json
import logging
from datetime import datetime
import PyPDF2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SocialMediaAnalyzer:
    """Social Media Cryptocurrency Analyzer"""

    def __init__(self):
        """Initialize the analyzer"""
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=self.api_key)
        self.model_name = os.environ.get('OPENAI_MODEL', 'gpt-4o')

        logger.info(f"Initializing Social Media Analyzer, using model: {self.model_name}")

    def read_pdf(self, pdf_path: str) -> str:
        """
        Read content from a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Text content of the PDF.
        """
        try:
            logger.info(f"Reading PDF file: {pdf_path}")

            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n\n"

            logger.info(f"Successfully read {len(pdf_reader.pages)} pages from PDF")
            return text

        except Exception as e:
            logger.error(f"Failed to read PDF: {str(e)}")
            raise

    def analyze_symbols(self, pdf_content: str, symbols: list) -> dict:
        """
        Analyze cryptocurrency symbols to find the one requiring the most attention.

        Args:
            pdf_content: Text content of the PDF.
            symbols: List of cryptocurrency symbols to analyze.

        Returns:
            JSON dictionary of the analysis result.
        """
        try:
            logger.info(f"Starting analysis for {len(symbols)} cryptocurrency symbols...")

            # Construct the prompt
            prompt = f"""You are a professional cryptocurrency market analyst and social media intelligence expert.

Please carefully read the following social media content from Key Opinion Leaders (KOLs) in the crypto industry:

{pdf_content}

---

Now, please analyze the following cryptocurrency symbols to identify the **symbol requiring the most attention**, and provide a detailed reason:

Symbol List: {', '.join(symbols)}

Analysis Dimensions:
1. **Social Media Mention Frequency**: Number of mentions and importance within the PDF content.
2. **KOL Attitude**: Attitudes and comments from KOLs (e.g., Justin Sun, He Yi, CZ, etc.) regarding the coin.
3. **Project Updates**: Mentioned project updates, partnerships, technical progress, etc.
4. **Market Sentiment**: Positive/Negative sentiment conveyed by social media.
5. **Potential Risks or Opportunities**: Risks or opportunities identified based on social media content.
6. **Exchange Support**: Support status from major exchanges like Binance.

Please return the analysis result in JSON format, containing only the one symbol that needs the most attention and the most important reason:
{{
    "symbol": "The symbol name requiring the most attention",
    "reason": "The most important reason and trend (one concise sentence) along with an estimated accuracy score (float between 0-1)"
}}

**IMPORTANT**: Return only a valid JSON object. Do not add any other explanatory text.
"""

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional cryptocurrency market analyst and social media intelligence expert, skilled at extracting key information from social media content and conducting in-depth analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )

            # Parse response
            result = json.loads(response.choices[0].message.content)

            logger.info("Analysis complete")
            return result

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def save_result(self, result: dict, output_path: str):
        """
        Save analysis result to a file.

        Args:
            result: Analysis result dictionary.
            output_path: Output file path.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save JSON result
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            logger.info(f"Analysis result saved to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to save result: {str(e)}")
            raise


def main():
    """Main function"""
    # Get project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Configuration parameters
    PDF_PATH = os.path.join(project_root, "Data.pdf")
    OUTPUT_PATH = os.path.join(project_root, "CODE_GEN/resources/social_media_analysis.txt")
    SYMBOLS = ["USDT", "BTC", "ETH", "USDC", "SOL", "XRP", "ZEC", "BNB", "DOGE"]

    # Create analyzer
    analyzer = SocialMediaAnalyzer()

    # Read PDF
    pdf_content = analyzer.read_pdf(PDF_PATH)

    # Analyze symbols
    result = analyzer.analyze_symbols(pdf_content, SYMBOLS)

    # Save result
    analyzer.save_result(result, OUTPUT_PATH)

    # Print result summary
    print("\n" + "="*80)
    print("Analysis Complete!")
    print("="*80)
    print(f"\nResult saved to: {OUTPUT_PATH}\n")

    if 'symbol' in result:
        print("Most noteworthy cryptocurrency:\n")
        print(f"  Symbol: {result['symbol']}")
        print(f"  Reason: {result['reason']}")
        print()


if __name__ == "__main__":
    main()