<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_test\Functional;

use Drupal\Tests\BrowserTestBase;

/**
 * Provides a base class for farmOS functional tests.
 */
abstract class FarmBrowserTestBase extends BrowserTestBase {

  /**
   * {@inheritdoc}
   */
  protected $profile = 'farm';

  /**
   * {@inheritdoc}
   */
  protected $defaultTheme = 'stark';

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {

    // Set a global farm_test variable and then delegate to the parent setUp().
    // This prevents farmOS base modules from being installed.
    // @see farm_install_base_modules()
    $GLOBALS['farm_test'] = TRUE;
    parent::setUp();
  }

}
