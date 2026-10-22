<?php

declare(strict_types=1);

namespace Drupal\Tests\data_stream\Kernel;

use Drupal\KernelTests\KernelTestBase;
use PHPUnit\Framework\Attributes\Group;
use Symfony\Component\HttpFoundation\Request;

/**
 * Tests for Data Streams.
 */
#[Group('farm')]
abstract class DataStreamTestBase extends KernelTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'system',
    'entity',
    'field',
    'fraction',
    'asset',
    'data_stream',
    'user',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $this->installEntitySchema('data_stream');
    $this->installConfig(['data_stream']);
    $this->installSchema('data_stream', 'data_stream_basic');
  }

  /**
   * Process a request.
   *
   * @param \Symfony\Component\HttpFoundation\Request $request
   *   The request.
   *
   * @return \Symfony\Component\HttpFoundation\Response
   *   The response.
   */
  protected function processRequest(Request $request) {
    return $this->container->get('http_kernel')->handle($request);
  }

}
