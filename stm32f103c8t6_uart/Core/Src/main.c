/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
UART_HandleTypeDef huart1;
UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */
#define TEST_BUF_SIZE 256
static uint8_t  tx_buf[TEST_BUF_SIZE];
static uint8_t  rx_buf[TEST_BUF_SIZE];
static uint32_t tests_passed = 0;
static uint32_t tests_failed = 0;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART2_UART_Init(void);
/* USER CODE BEGIN PFP */
static void   uart_loopback_test(void);
static int    test_single_byte(void);
static int    test_variable_length(void);
static int    test_edge_patterns(void);
static void   led_init(void);
static void   led_pass(void);
static void   led_fail(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* ---------------------------------------------------------- */
/* printf retarget to USART1                                  */
/* ---------------------------------------------------------- */
int __io_putchar(int ch)
{
  HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 2000);
  return ch;
}

/* ---------------------------------------------------------- */
/* LED helpers — PC13, active-low on Blue Pill                */
/* ---------------------------------------------------------- */
static void led_init(void)
{
  __HAL_RCC_GPIOC_CLK_ENABLE();
  GPIO_InitTypeDef g = {0};
  g.Pin   = GPIO_PIN_13;
  g.Mode  = GPIO_MODE_OUTPUT_PP;
  g.Pull  = GPIO_NOPULL;
  g.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &g);
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);  // LED off
}
static void led_pass(void)
{
  for (int i = 0; i < 6; i++) {
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
    HAL_Delay(80);
  }
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
}

static void led_fail(void)
{
  for (int i = 0; i < 3; i++) {
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
    HAL_Delay(300);
  }
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
}

/* ---------------------------------------------------------- */
/* UART loopback test cases                                   */
/* ---------------------------------------------------------- */
static int uart_check(const char *name, uint32_t len)
{
  memset(rx_buf, 0, len);
  HAL_UART_Transmit(&huart2, tx_buf, len, 2000);
  HAL_UART_Receive(&huart2, rx_buf, len, 2000);

  if (memcmp(tx_buf, rx_buf, len) != 0) {
    printf("  FAIL: %s\n", name);
    return 0;
  }
  printf("  PASS: %s\n", name);
  return 1;
}

static int test_single_byte(void)
{
  printf("  [Single-byte 0x00..0xFF]\n");
  int errors = 0;
  for (int v = 0; v < 256; v++) {
    tx_buf[0] = (uint8_t)v;
    memset(rx_buf, 0, 1);
    HAL_UART_Transmit(&huart2, tx_buf, 1, 2000);
    HAL_UART_Receive(&huart2, rx_buf, 1, 2000);
    if (rx_buf[0] != (uint8_t)v) {
      errors++;
      if (errors <= 5)
        printf("  FAIL: sent 0x%02X got 0x%02X\n", v, rx_buf[0]);
    }
  }
  if (errors == 0) {
    printf("  PASS: 256/256\n");
    return 1;
  }
  printf("  FAIL: %d/256 errors\n", errors);
  return 0;
}

static int test_variable_length(void)
{
  printf("  [Variable-length packets]\n");
  int all_ok = 1;
  uint32_t lens[] = {1, 4, 16, 64, 256};
  char name[32];
  for (int i = 0; i < 5; i++) {
    uint32_t n = lens[i];
    for (uint32_t j = 0; j < n; j++) tx_buf[j] = (uint8_t)(j & 0xFF);
    sprintf(name, "len=%lu", n);
    if (!uart_check(name, n)) all_ok = 0;
  }
  return all_ok;
}

static int test_edge_patterns(void)
{
  printf("  [Edge patterns]\n");
  int all_ok = 1;

  memset(tx_buf, 0x00, 64); if (!uart_check("all-0x00", 64)) all_ok = 0;
  memset(tx_buf, 0xFF, 64); if (!uart_check("all-0xFF", 64)) all_ok = 0;
  memset(tx_buf, 0x55, 64); if (!uart_check("0x55-alt", 64)) all_ok = 0;
  memset(tx_buf, 0xAA, 64); if (!uart_check("0xAA-alt", 64)) all_ok = 0;

  for (int i = 0; i < 64; i++) tx_buf[i] = (uint8_t)i;
  if (!uart_check("inc-0..63", 64)) all_ok = 0;

  for (int i = 0; i < 64; i++) tx_buf[i] = (uint8_t)(63 - i);
  if (!uart_check("dec-63..0", 64)) all_ok = 0;

  return all_ok;
}

static void uart_loopback_test(void)
{
  int ok;

  printf("\n--- USART2 Loopback @ 115200 ---\n");

  ok = test_single_byte();     ok ? tests_passed++ : tests_failed++;
  ok = test_variable_length(); ok ? tests_passed++ : tests_failed++;
  ok = test_edge_patterns();   ok ? tests_passed++ : tests_failed++;
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART1_UART_Init();
  MX_USART2_UART_Init();
  /* USER CODE BEGIN 2 */

  /* Init LED */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  GPIO_InitTypeDef g = {0};
  g.Pin   = GPIO_PIN_13;
  g.Mode  = GPIO_MODE_OUTPUT_PP;
  g.Pull  = GPIO_NOPULL;
  g.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &g);
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);

  /* Signal ready: 3 fast blinks */
  for (int i = 0; i < 3; i++) {
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
    HAL_Delay(100);
  }
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);

  printf("\nSTM32 Echo Server ready\r\n");
  printf("USART2 (PA2/PA3) @ 115200\r\n\n");

  /* Buffered echo: collect packet, echo with delay */
  uint8_t buf[256];
  while (1) {
    uint32_t count = 0;
    uint32_t deadline = HAL_GetTick() + 5;

    while (count < 256) {
      if (HAL_UART_Receive(&huart2, &buf[count], 1, 2) == HAL_OK) {
        count++;
        deadline = HAL_GetTick() + 5;
        GPIOC->ODR ^= GPIO_ODR_ODR13;
      } else if ((int32_t)(HAL_GetTick() - deadline) > 0) {
        break;
      }
    }

    if (count > 0) {
      HAL_UART_Transmit(&huart2, buf, count, 5000);
    }
  }
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief USART1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART1_UART_Init(void)
{

  /* USER CODE BEGIN USART1_Init 0 */

  /* USER CODE END USART1_Init 0 */

  /* USER CODE BEGIN USART1_Init 1 */

  /* USER CODE END USART1_Init 1 */
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART1_Init 2 */

  /* USER CODE END USART1_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
