<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Plugin\SetupForm;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\farm_setup\Attribute\SetupForm;

/**
 * Welcome step for the farmOS setup wizard.
 */
#[SetupForm(
  id: 'welcome',
  title: new TranslatableMarkup('Welcome to farmOS'),
  task_title: new TranslatableMarkup('Welcome'),
  description: new TranslatableMarkup('This will guide you through the process of setting up your farmOS system.'),
  weight: -100,
)]
class SetupWelcomeForm extends SetupFormBase {

}
