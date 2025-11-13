# main.py
import os
import sys
import argparse
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stages.stage1_project_parser import run_stage1
from stages.stage2_symbol_extractor import run_stage2
from stages.stage3_relation_builder import run_stage3
from stages.stage4_knowledge_graph import run_stage4
from stages.stage5_semantic_embedder import run_stage5
from stages.stage6_query_processor import run_stage6_query
from stages.stage7_answer_generator import run_stage7_answer


def run_all_stages(project_path: str, output_dir: str = "data/processed"):
    """运行所有阶段"""
    print("=" * 60)
    print("开始运行代码理解智能体")
    print("=" * 60)

    # 阶段1: 项目解析
    print("\n🎯 阶段1: 项目解析")
    stage1_output = run_stage1(project_path)

    # 阶段2: 符号提取
    print("\n🎯 阶段2: 符号提取")
    stage2_output = run_stage2(stage1_output)

    # 阶段3: 关系构建
    print("\n🎯 阶段3: 关系构建")
    stage3_output = run_stage3(stage2_output)

    # 阶段4: 知识图谱
    print("\n🎯 阶段4: 知识图谱构建")
    stage4_output = run_stage4(stage3_output)

    # 阶段5: 语义嵌入
    print("\n🎯 阶段5: 语义嵌入")
    stage5_output = run_stage5(stage4_output)

    print("\n✅ 所有阶段完成!")
    print(f"输出文件保存在: {output_dir}")

    return stage5_output


def run_query_mode(stage5_output_file: str):
    """运行查询模式"""
    print("\n🔍 进入查询模式")
    print("输入 'quit' 或 'exit' 退出")

    while True:
        try:
            user_query = input("\n请输入您的问题: ").strip()

            if user_query.lower() in ['quit', 'exit']:
                print("再见!")
                break

            if not user_query:
                continue

            # 处理查询
            query_result = run_stage6_query(stage5_output_file, user_query)

            # 生成答案
            answer = run_stage7_answer(stage5_output_file, query_result, user_query)

            # 显示答案
            print("\n" + "=" * 50)
            print("🤖 答案:")
            print("=" * 50)
            print(answer.get("answer", "抱歉，没有生成答案。"))

            # 显示额外信息
            if "key_points" in answer:
                print("\n📌 关键要点:")
                for point in answer["key_points"]:
                    print(f"  • {point}")

            if "implementation_steps" in answer:
                print("\n🔧 实现步骤:")
                for step in answer["implementation_steps"]:
                    print(f"  {step}")

            if "navigation" in answer:
                print("\n📍 导航信息:")
                for nav in answer["navigation"]:
                    print(f"  • {nav['name']} ({nav['type']}) - {nav['location']}")

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n❌ 处理查询时出错: {e}")


def main():
    parser = argparse.ArgumentParser(description='代码理解智能体')
    parser.add_argument('D:\other\spdlog-1.x', nargs='?', help='要分析的C++项目路径')
    parser.add_argument('--query', '-q', action='store_true', help='进入查询模式')
    parser.add_argument('--stage5-file', help='阶段5输出文件（用于查询模式）')

    args = parser.parse_args()

    if args.query:
        # 查询模式
        if args.stage5_file and os.path.exists(args.stage5_file):
            run_query_mode(args.stage5_file)
        else:
            # 查找最新的阶段5文件
            processed_dir = "data/processed"
            if os.path.exists(processed_dir):
                stage5_files = [f for f in os.listdir(processed_dir) if f.startswith("stage5")]
                if stage5_files:
                    latest_file = os.path.join(processed_dir, sorted(stage5_files)[-1])
                    run_query_mode(latest_file)
                else:
                    print("❌ 没有找到阶段5输出文件，请先运行分析模式")
            else:
                print("❌ 没有找到处理数据目录，请先运行分析模式")
    else:
        # 分析模式
        if not args.project_path:
            print("❌ 请提供要分析的C++项目路径")
            return

        if not os.path.exists(args.project_path):
            print(f"❌ 项目路径不存在: {args.project_path}")
            return

        stage5_output = run_all_stages(args.project_path)

        # 询问是否进入查询模式
        response = input("\n是否进入查询模式? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            run_query_mode(stage5_output)


if __name__ == "__main__":
    main()