from analysis.learner_resolver import LearnerResolver

resolver = LearnerResolver("data/master_student_clean.csv")

print("\n--- EMAIL TEST ---")
print(resolver.resolve(
    email="test@example.com",
    source_system="efset"
))

print("\n--- EXTERNAL ID TEST ---")
print(resolver.resolve(
    external_id="ID_LRN_432786",
    source_system="quill"
))

print("\n--- NAME TEST ---")
print(resolver.resolve(
    name="Munyampeta David",
    source_system="northstar"
))

print("\n--- EMPTY TEST ---")
print(resolver.resolve(
    source_system="unknown"
))
