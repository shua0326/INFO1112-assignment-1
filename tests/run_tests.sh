#!/bin/bash

# Define the paths to the test cases
input_dir="./io_files"
output_dir="./io_files"
script="../mysh.py"

# Function to run a single test case
run_test() {
    local test_case=$1
    local input_file="${input_dir}/${test_case}.in"
    local expected_output_file="${output_dir}/${test_case}.out"
    local actual_output_file="${output_dir}/${test_case}.actual"

    # Run the Python script with the input file and capture the output
    python3 ../mysh.py < $input_file > "$actual_output_file" 2>&1

    # Compare the actual output with the expected output
    if diff -su "$actual_output_file" "$expected_output_file" > /dev/null; then
        echo "Test $test_case: PASSED"
    else
        echo "Test $test_case: FAILED"
        echo "Expected:"
        cat "$expected_output_file"
        echo "Actual:"
        cat "$actual_output_file"
    fi

    # Clean up the actual output file
    rm "$actual_output_file"
}

# Define the test cases and iterate over them
ls io_files | sed 's/\.[^.]*$//' | sort | uniq | while read test_case; do
    run_test "$test_case"
done
