from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_management import file_management_agent, ChangeDetector, IndexWorker

def test_change_detector():
    detector = ChangeDetector(threshold=0.05)
    
    old_content = "Hello World"
    new_content = "Hello World!"
    print(f"Test 1 - Minor change (adding exclamation):")
    print(f"  Similarity: {detector.calculate_similarity(old_content, new_content):.4f}")
    print(f"  Diff ratio: {detector.calculate_diff_ratio(old_content, new_content):.4f}")
    print(f"  Should block: {detector.should_block(old_content, new_content)}")
    print()
    
    old_content = "This is a test document with some content."
    new_content = "This is a test document with some modified content."
    print(f"Test 2 - Moderate change:")
    print(f"  Similarity: {detector.calculate_similarity(old_content, new_content):.4f}")
    print(f"  Diff ratio: {detector.calculate_diff_ratio(old_content, new_content):.4f}")
    print(f"  Should block: {detector.should_block(old_content, new_content)}")
    print()
    
    old_content = "Original content"
    new_content = "Completely different content that is much longer and has different meaning."
    print(f"Test 3 - Major change:")
    print(f"  Similarity: {detector.calculate_similarity(old_content, new_content):.4f}")
    print(f"  Diff ratio: {detector.calculate_diff_ratio(old_content, new_content):.4f}")
    print(f"  Should block: {detector.should_block(old_content, new_content)}")
    print()

def test_file_management_agent():
    base_dir = Path(__file__).parent
    file_management_agent.configure(base_dir)
    
    test_file = base_dir / "knowledge" / "test_file.md"
    original_content = "# Test Document\n\nThis is a test document for the file management agent.\n\nIt contains some sample content."
    
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(original_content, encoding="utf-8")
    print(f"Created test file: {test_file}")
    print()
    
    print("Test 1 - Handle user save with minor change:")
    minor_change = "# Test Document\n\nThis is a test document for the file management agent.\n\nIt contains some sample content."
    result = file_management_agent.handle_user_save(str(test_file), minor_change)
    print(f"  Result: {result}")
    print()
    
    print("Test 2 - Handle user save with actual change:")
    modified_content = "# Test Document\n\nThis is a MODIFIED test document for the file management agent.\n\nIt contains some sample content that has been updated."
    result = file_management_agent.handle_user_save(str(test_file), modified_content)
    print(f"  Result: {result}")
    print()
    
    print("Test 3 - Handle user delete:")
    result = file_management_agent.handle_user_delete(str(test_file))
    print(f"  Result: {result}")
    print()
    
    print("Test 4 - Handle user create:")
    new_file = base_dir / "knowledge" / "new_file.md"
    new_content = "# New Document\n\nThis is a newly created document."
    result = file_management_agent.handle_user_create(str(new_file), new_content)
    print(f"  Result: {result}")
    print()
    
    new_file.unlink(missing_ok=True)
    print("Cleanup completed")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing ChangeDetector")
    print("=" * 60)
    test_change_detector()
    
    print("=" * 60)
    print("Testing FileManagementAgent")
    print("=" * 60)
    test_file_management_agent()
