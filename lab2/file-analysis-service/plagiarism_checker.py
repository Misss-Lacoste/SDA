import re  #регексы, регексы, мои регексы
from typing import List, Dict, Tuple
import hashlib  #вот так мощно по хэшам
from difflib import SequenceMatcher  #для сравния последовательностей

class PlagiarismChecker:
    """
    (справочка)
    Извлекаем текст из файла, потом приводим к общему виду, удаляя пробелы + нижний регистр ->
    cравниваем с другими работами и ->
    определяем процент схожести!
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
            similarity_threshold: Порог схожести для определения плагиата (0.0-1.0 aka полное совпадение)
        """
        self.similarity_threshold = similarity_threshold
    
    def normalize_text(self, text: str) -> str:
        """Общий вид текста для сравнения"""
        #к нижнему регистру
        text = text.lower()
        #удаление всех небуквенных символы, кроме пробела
        text = re.sub(r'[^a-zа-яё\s]', '', text)
        #минус лишние пробелы(но не минус вайб)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Схожесть между двумя текстами"""
        if not text1 or not text2:
            return 0.0
        
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    def extract_text_fingerprint(self, text: str, block_size: int = 50) -> List[str]:
        """Создает отпечатки текста для сравнения"""
        words = text.split()
        fingerprints = []
        
        for i in range(0, len(words), block_size):
            block = ' '.join(words[i:i + block_size])
            # Создаем хэш для каждого блока
            block_hash = hashlib.md5(block.encode()).hexdigest()[:8]
            fingerprints.append(block_hash)
        
        return fingerprints
    
    def check_plagiat(self, current_text: str, previous_texts: List[str]) -> Dict:
        if not previous_texts:
            return {
                "is_plagiat": False,
                "similarity_score": 0.0,
                "most_similar_work_index": -1,
                "comparison_details": []
            }
        
        normalized_current = self.normalize_text(current_text)
        current_fingerprints = self.extract_text_fingerprint(normalized_current)
        
        similarities = []
        comparison_details = []
        
        for idx, prev_text in enumerate(previous_texts):
            normalized_prev = self.normalize_text(prev_text)
            
            similarity = self.calculate_similarity(normalized_current, normalized_prev)
            similarities.append(similarity)
            
            prev_fingerprints = self.extract_text_fingerprint(normalized_prev)
            
            matching_fingerprints = len(set(current_fingerprints) & set(prev_fingerprints))
            total_fingerprints = len(set(current_fingerprints) | set(prev_fingerprints))
            
            fingerprint_similarity = matching_fingerprints / total_fingerprints if total_fingerprints > 0 else 0
            
            comparison_details.append({
                "work_index": idx,
                "text_similarity": round(similarity, 3),
                "fingerprint_similarity": round(fingerprint_similarity, 3),
                "combined_similarity": round((similarity + fingerprint_similarity) / 2, 3)
            })
        
        max_similarity = max(similarities) if similarities else 0.0
        most_similar_index = similarities.index(max_similarity) if similarities else -1
        
        is_plagiat = max_similarity >= self.similarity_threshold
        return {
            "is_plagiat": is_plagiat,
            "similarity_score": round(max_similarity, 3),
            "most_similar_work_index": most_similar_index,
            "threshold": self.similarity_threshold,
            "comparison_details": comparison_details,
            "total_works_compared": len(previous_texts)
        }
    
    def generate_report(self, plagiat_result: Dict, current_work_info: Dict = None) -> Dict:
        """Детальный отчет о проверке плагиата"""
        report = {
            "summary": {
                "plagiat_detected": plagiat_result["is_plagiat"],
                "similarity_score": plagiat_result["similarity_score"],
                "threshold": plagiat_result["threshold"]
            },
            "details": plagiat_result.get("comparison_details", []),
            "statistics": {
                "total_comparisons": plagiat_result.get("total_works_compared", 0),
                "most_similar_work": plagiat_result.get("most_similar_work_index", -1)
            }
        }
        
        if current_work_info:
            report["work_info"] = current_work_info
        
        if plagiat_result["is_plagiat"]:
            report["recommendations"] = [
                "Подозрение в плагиате"
            ]
        else:
            report["recommendations"] = [
                "Уровень оригинальности приемлемый"
            ]
        
        return report
    
if __name__ == "__main__":
    checker = PlagiarismChecker(similarity_threshold=0.7)
    
    text1 = "Сидит кошка на окошке, к ней подходит бригадир."
    #text2 = "Сидит кошка на окошке, к ней подходит бригадир."  #копия
    text3 = "Иди, кошка, на работу, а то хлеба не дадим."
    
    result = checker.check_plagiat(text1, text3) #для маленького тестика можно тест3 сюда вписать, на консольку все отлично выводится
    print("Результат проверки плагиата:")
    print(f"Обнаружен плагиат: {result['is_plagiat']}")
    print(f"Схожесть: {result['similarity_score']}")
    
    report = checker.generate_report(result, {"student": "Виденин С.А.", "assignment": "homework3"})
    print("\nОтчет:")
    print(report)