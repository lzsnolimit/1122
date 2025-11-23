"""
分析 Data.pdf 中的社交媒体内容，找出最需要关注的加密货币符号
"""

from openai import OpenAI
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import PyPDF2

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SocialMediaAnalyzer:
    """社交媒体加密货币分析器"""

    def __init__(self):
        """初始化分析器"""
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 环境变量未设置")

        self.client = OpenAI(api_key=self.api_key)
        self.model_name = os.environ.get('OPENAI_MODEL', 'gpt-4o')

        logger.info(f"初始化社交媒体分析器，使用模型: {self.model_name}")

    def read_pdf(self, pdf_path: str) -> str:
        """
        读取 PDF 文件内容

        Args:
            pdf_path: PDF 文件路径

        Returns:
            PDF 文本内容
        """
        try:
            logger.info(f"正在读取 PDF 文件: {pdf_path}")

            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n\n"

            logger.info(f"成功读取 {len(pdf_reader.pages)} 页 PDF 内容")
            return text

        except Exception as e:
            logger.error(f"读取 PDF 失败: {str(e)}")
            raise

    def analyze_symbols(self, pdf_content: str, symbols: list) -> dict:
        """
        分析加密货币符号，找出最需要关注的

        Args:
            pdf_content: PDF 文本内容
            symbols: 要分析的加密货币符号列表

        Returns:
            分析结果的 JSON 字典
        """
        try:
            logger.info(f"开始分析 {len(symbols)} 个加密货币符号...")

            # 构建提示词
            prompt = f"""你是一位专业的加密货币市场分析师和社交媒体情报分析专家。

请仔细阅读以下来自加密货币行业关键意见领袖（KOL）的社交媒体内容：

{pdf_content}

---

现在，请分析以下加密货币符号，找出**最需要关注（attention）的符号**，并提供详细的理由：

符号列表：{', '.join(symbols)}

分析维度：
1. **社交媒体提及频率**：在 PDF 内容中被提及的次数和重要性
2. **关键人物态度**：孙宇晨、何一、赵长鹏等 KOL 对该币种的态度和评论
3. **项目动态**：提到的项目更新、合作、技术进展等
4. **市场情绪**：社交媒体传递的正面/负面情绪
5. **潜在风险或机会**：基于社交媒体内容识别的风险点或机会点
6. **交易所支持**：币安等主要交易所的支持情况

请以 JSON 格式返回分析结果，只包含最需要关注的一个 symbol 和一个最重要的原因：
{{
    "symbol": "最需要关注的符号名称",
    "reason": "最重要的需要关注的原因（一句话，简洁明了）"
}}

**重要**：只返回有效的 JSON 对象，不要添加其他解释文字。
"""

            # 调用 OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的加密货币市场分析师和社交媒体情报分析专家，擅长从社交媒体内容中提取关键信息并进行深度分析。"
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

            # 解析响应
            result = json.loads(response.choices[0].message.content)

            logger.info("分析完成")
            return result

        except Exception as e:
            logger.error(f"分析失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def save_result(self, result: dict, output_path: str):
        """
        保存分析结果到文件

        Args:
            result: 分析结果字典
            output_path: 输出文件路径
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 保存 JSON 结果
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            logger.info(f"分析结果已保存到: {output_path}")

        except Exception as e:
            logger.error(f"保存结果失败: {str(e)}")
            raise


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # 配置参数
    PDF_PATH = os.path.join(project_root, "Data.pdf")
    OUTPUT_PATH = os.path.join(project_root, "CODE_GEN/resources/social_media_analysis.txt")
    SYMBOLS = ["USDT", "BTC", "ETH", "USDC", "SOL", "XRP", "ZEC", "BNB", "DOGE"]

    # 创建分析器
    analyzer = SocialMediaAnalyzer()

    # 读取 PDF
    pdf_content = analyzer.read_pdf(PDF_PATH)

    # 分析符号
    result = analyzer.analyze_symbols(pdf_content, SYMBOLS)

    # 保存结果
    analyzer.save_result(result, OUTPUT_PATH)

    # 打印结果摘要
    print("\n" + "="*80)
    print("分析完成！")
    print("="*80)
    print(f"\n结果已保存到: {OUTPUT_PATH}\n")

    if 'symbol' in result:
        print("最需要关注的加密货币：\n")
        print(f"  Symbol: {result['symbol']}")
        print(f"  原因: {result['reason']}")
        print()


if __name__ == "__main__":
    main()