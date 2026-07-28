#!/bin/bash

# Configuration
export PYTHONPATH="$(pwd)/runtime"
REPORT_FILE="verification_report.txt"
DATE_RUN=$(date)

# UI Elements
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}   Broccoli Core Production Verification        ${NC}"
echo -e "${YELLOW}================================================${NC}"

echo "Broccoli Core Verification Report" > $REPORT_FILE
echo "Run Date: $DATE_RUN" >> $REPORT_FILE
echo "------------------------------------------------" >> $REPORT_FILE

run_suite() {
    SUITE_NAME=$1
    DIR=$2
    echo -e "\n${YELLOW}Running $SUITE_NAME Tests...${NC}"
    echo -e "\n--- $SUITE_NAME TESTS ---" >> $REPORT_FILE
    
    python3 -m unittest discover -s "$DIR" -p "test_*.py" -v > temp_result.log 2>&1
    EXIT_CODE=$?
    
    cat temp_result.log >> $REPORT_FILE
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✓ $SUITE_NAME Tests Passed${NC}"
    else
        echo -e "${RED}✗ $SUITE_NAME Tests Failed (See report for details)${NC}"
    fi
    rm temp_result.log
    return $EXIT_CODE
}

run_suite "Unit" "tests"
UNIT_EXIT=$?

run_suite "Integration" "integration"
INT_EXIT=$?

run_suite "Simulation & Stress" "simulation"
SIM_EXIT=$?

echo -e "\n${YELLOW}================================================${NC}"
echo -e "Final Results:"
if [ $UNIT_EXIT -eq 0 ] && [ $INT_EXIT -eq 0 ] && [ $SIM_EXIT -eq 0 ]; then
    echo -e "${GREEN}ALL VERIFICATIONS PASSED SUCCESSFULLY.${NC}"
    echo "STATUS: PASSED" >> $REPORT_FILE
else
    echo -e "${RED}VERIFICATION FAILED. Check verification_report.txt for details.${NC}"
    echo "STATUS: FAILED" >> $REPORT_FILE
fi
echo -e "${YELLOW}================================================${NC}"

echo -e "Detailed report saved to: ${GREEN}$REPORT_FILE${NC}"
